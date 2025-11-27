import os
import requests
from tqdm import tqdm

def download_preview(url, save_path):
    """
    Args:
        url (str): The URL of the audio file.
        save_path (str): The local path to save the file.    
    Returns:
        success (bool): True if successful, False otherwise.
    """
    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()
        
        with open(save_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        return True
    except Exception as e:
        print(f"Error downloading {url}: {e}")
        if os.path.exists(save_path):
            os.remove(save_path)
        return False

def batch_download(tracks, output_dir):
    """
    Args:
        tracks (list): List of track dictionaries from the API.
        output_dir (str): Directory to save files.
        
    Returns:
        downloaded_paths (list): List of paths to downloaded files.
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    downloaded_paths = []
    
    print(f"Downloading {len(tracks)} tracks to {output_dir}...")
    
    for track in tqdm(tracks, desc="Downloading previews"):
        preview_url = track.get("previewUrl")
        if not preview_url:
            continue
            
        artist = track.get("artistName", "Unknown").replace("/", "_")
        name = track.get("trackName", "Unknown").replace("/", "_")
        filename = f"{artist} - {name}.m4a"
        save_path = os.path.join(output_dir, filename)
        
        if os.path.exists(save_path):
            downloaded_paths.append(save_path)
            continue
            
        if download_preview(preview_url, save_path):
            downloaded_paths.append(save_path)
            
    return downloaded_paths
