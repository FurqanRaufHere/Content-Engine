import os
import random
import requests
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("PEXELS_API_KEY")

def download_video(query, output_path):
    print(f"🎥 Searching Pexels for: '{query}'...")
    
    if not API_KEY:
        print("❌ Error: PEXELS_API_KEY missing.")
        return None

    headers = {"Authorization": API_KEY}
    # Request 15 videos instead of 1 to get variety
    url = f"https://api.pexels.com/videos/search?query={query}&per_page=15&orientation=portrait"
    
    try:
        response = requests.get(url, headers=headers)
        data = response.json()
        
        if not data['videos']:
            print(f"⚠️ No videos found for '{query}'. Using backup.")
            return download_video("abstract", output_path)
            
        # --- THE FIX: RANDOM SELECTION ---
        # Filter for HD videos (width >= 1080)
        hd_videos = [v for v in data['videos'] if v['video_files'][0]['width'] >= 1080]
        
        # If we have HD videos, pick a random one. If not, pick random from any.
        candidates = hd_videos if hd_videos else data['videos']
        
        # Pick a RANDOM video from the candidates
        video_data = random.choice(candidates)
        # ---------------------------------
        
        # Get best quality link for that specific video
        video_files = video_data['video_files']
        best_video = sorted(video_files, key=lambda x: x['width'], reverse=True)[0]
        download_url = best_video['link']
        
        print(f"   ⬇️ Downloading video (ID: {video_data['id']})...")
        
        with requests.get(download_url, stream=True) as r:
            r.raise_for_status()
            with open(output_path, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
                    
        print(f"✅ Video saved to: {output_path}")
        return output_path

    except Exception as e:
        print(f"❌ Visuals Error: {e}")
        return None

# import os
# import requests
# from dotenv import load_dotenv

# # Load API Key
# load_dotenv()
# API_KEY = os.getenv("PEXELS_API_KEY")

# def download_video(query, output_path="assets/temp/background.mp4"):
#     print(f"🎥 Searching Pexels for: '{query}'...")
    
#     if not API_KEY:
#         print("❌ Error: PEXELS_API_KEY not found in .env")
#         return None

#     # 1. Search API (Filter for Vertical/Portrait)
#     headers = {"Authorization": API_KEY}
#     url = f"https://api.pexels.com/videos/search?query={query}&per_page=1&orientation=portrait"
    
#     try:
#         response = requests.get(url, headers=headers)
#         data = response.json()
        
#         if not data['videos']:
#             print(f"⚠️ No videos found for '{query}'. Trying generic backup.")
#             return download_video("abstract", output_path)
            
#         # 2. Get the Best Video Link
#         video_data = data['videos'][0]
#         video_files = video_data['video_files']
        
#         # Sort by quality (highest width first) to get 1080p/4k
#         best_video = sorted(video_files, key=lambda x: x['width'], reverse=True)[0]
#         download_url = best_video['link']
        
#         print(f"   ⬇️ Downloading video (ID: {video_data['id']})...")
        
#         # 3. Download Stream
#         with requests.get(download_url, stream=True) as r:
#             r.raise_for_status()
#             os.makedirs(os.path.dirname(output_path), exist_ok=True)
#             with open(output_path, 'wb') as f:
#                 for chunk in r.iter_content(chunk_size=8192):
#                     f.write(chunk)
                    
#         print(f"✅ Video saved to: {output_path}")
#         return output_path

#     except Exception as e:
#         print(f"❌ Visuals Error: {e}")
#         return None

# if __name__ == "__main__":
#     # Test Run
#     download_video("Fitness")