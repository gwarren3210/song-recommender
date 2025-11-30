import requests
import re
from typing import List, Dict, Optional

class AppleMusicClient:
    BASE_URL = "https://itunes.apple.com/search"
    LOOKUP_URL = "https://itunes.apple.com/lookup"

    def __init__(self):
        """Initialize Apple Music client."""

    def search(self, term, limit=20, entity="song", media="music", country_code=None):
        """
        Searches for tracks on Apple Music/iTunes.
        
        Args:
            term (str): The search query (e.g., "Taylor Swift").
            limit (int): Max number of results.
            entity (str): The entity type to search for.
            media (str): The media type.
            country_code (str): ISO country code (e.g., 'us', 'be') for country-specific search
            
        Returns:
            results (list): List of track dictionaries.
        """
        params = {
            "term": term,
            "limit": limit,
            "entity": entity,
            "media": media
        }
        if country_code:
            params["country"] = country_code.lower()
        
        try:
            response = requests.get(self.BASE_URL, params=params)
            response.raise_for_status()
            data = response.json()
            return data.get("results", [])
        except Exception as e:
            print(f"Error searching Apple Music: {e}")
            return []

    def get_track_from_url(self, track_url: str) -> Optional[Dict]:
        """
        Get track information from an Apple Music/iTunes track URL using Lookup API.
        
        Args:
            track_url (str): Apple Music or iTunes track URL
            
        Returns:
            track_data (dict): Track dictionary with full iTunes API data, or None if not found
        """
        track_id = self._extract_track_id(track_url)
        if not track_id:
            print(f"Could not extract track ID from URL: {track_url}")
            return None
        
        country_code = self._extract_country_code(track_url)
        result = self.lookup_track(track_id, track_url, country_code)
        
        # If direct lookup fails, try searching by track name from URL
        if not result:
            track_name = self._extract_track_name(track_url)
            if track_name:
                print(f"  Attempting search fallback for: {track_name}")
                search_results = self.search(track_name, limit=5, entity="song", media="music")
                if search_results:
                    # Return first result that looks like a match
                    # (could be improved with better matching logic)
                    return search_results[0]
        
        return result

    def lookup_track(self, track_id: str, original_url: str = None, country_code: str = None) -> Optional[Dict]:
        """
        Lookup track information using iTunes Lookup API.
        
        Args:
            track_id (str): iTunes track ID
            original_url (str): Original URL for better error messages
            country_code (str): ISO country code (e.g., 'us', 'be') for country-specific lookup
            
        Returns:
            track_data (dict): Track dictionary with full iTunes API data, or None if not found
        """
        try:
            params = {"id": track_id}
            if country_code:
                params["country"] = country_code.lower()
            
            response = requests.get(self.LOOKUP_URL, params=params)
            response.raise_for_status()
            data = response.json()
            
            results = data.get("results", [])
            if not results:
                # Try without country code as fallback if country was specified
                if country_code:
                    params_no_country = {"id": track_id}
                    response = requests.get(self.LOOKUP_URL, params=params_no_country)
                    response.raise_for_status()
                    data = response.json()
                    results = data.get("results", [])
                
                if not results:
                    if original_url:
                        print(f"  No results from iTunes API for track ID {track_id} (URL: {original_url})")
                    else:
                        print(f"  No results from iTunes API for track ID {track_id}")
                    return None
            
            # Check if first result is a track
            first_result = results[0]
            if first_result.get("wrapperType") == "track":
                return first_result
            
            # If not a track, log what we got
            wrapper_type = first_result.get("wrapperType", "unknown")
            if original_url:
                print(f"  iTunes API returned {wrapper_type} instead of track for ID {track_id} (URL: {original_url})")
            else:
                print(f"  iTunes API returned {wrapper_type} instead of track for ID {track_id}")
            return None
        except Exception as e:
            if original_url:
                print(f"  Error looking up track {track_id} (URL: {original_url}): {e}")
            else:
                print(f"  Error looking up track {track_id}: {e}")
            return None

    def get_tracks_from_urls(self, track_urls: List[str]) -> List[Dict]:
        """
        Get track information from a list of Apple Music/iTunes track URLs.
        
        Args:
            track_urls (list): List of Apple Music or iTunes track URLs
            
        Returns:
            tracks (list): List of track dictionaries with full iTunes API data
        """
        tracks = []
        for url in track_urls:
            url = url.strip()
            if not url:
                continue
            
            track_data = self.get_track_from_url(url)
            if track_data:
                tracks.append(track_data)
            else:
                print(f"Skipping invalid URL: {url}")
        
        return tracks

    def _extract_track_id(self, url: str) -> Optional[str]:
        """
        Extract track ID from Apple Music or iTunes URL.
        
        Supports formats like:
        - https://music.apple.com/be/song/levels-radio-edit/1442882814
        - https://itunes.apple.com/us/song/id1442882814
        - https://music.apple.com/us/album/.../1442882814?i=...
        """
        url = url.strip()
        
        # Remove query parameters
        if '?' in url:
            url = url.split('?')[0]
        
        # Try to extract numeric ID from end of URL
        # Apple Music URLs: .../song/title/ID or .../album/.../ID?i=...
        parts = url.rstrip('/').split('/')
        last_part = parts[-1] if parts else ""
        
        # Check if last part is a numeric ID
        if last_part.isdigit():
            return last_part
        
        # Try regex pattern for URLs with /id123456 format
        pattern = r'/id(\d+)'
        match = re.search(pattern, url)
        if match:
            return match.group(1)
        
        # Try to find any numeric ID in the URL
        pattern = r'/(\d+)(?:\?|$)'
        match = re.search(pattern, url)
        if match:
            return match.group(1)
        
        return None
    
    def _extract_country_code(self, url: str) -> Optional[str]:
        """
        Extract country code from Apple Music or iTunes URL.
        
        Supports formats like:
        - https://music.apple.com/be/song/...
        - https://itunes.apple.com/us/song/...
        
        Returns:
            ISO country code (e.g., 'be', 'us') or None if not found
        """
        url = url.strip()
        
        # Pattern for music.apple.com/{country}/...
        pattern = r'://(?:music|itunes)\.apple\.com/([a-z]{2})/'
        match = re.search(pattern, url, re.IGNORECASE)
        if match:
            return match.group(1).lower()
        
        return None
    
    def _extract_track_name(self, url: str) -> Optional[str]:
        """
        Extract track name from Apple Music URL for fallback search.
        
        Supports formats like:
        - https://music.apple.com/be/song/levels-radio-edit/1442882814
        - https://music.apple.com/be/song/mammoth/1111775125
        
        Returns:
            Track name (e.g., 'levels-radio-edit') or None if not found
        """
        url = url.strip()
        
        # Pattern for .../song/{track-name}/{id}
        pattern = r'/song/([^/]+)/\d+'
        match = re.search(pattern, url)
        if match:
            # Replace hyphens with spaces and clean up
            track_name = match.group(1).replace('-', ' ').replace('_', ' ')
            return track_name
        
        return None
