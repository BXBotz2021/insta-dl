import os
import sys
import requests
from pyrogram import Client, filters
from pyrogram.types import Message

try:
    from instagrapi import Client as InstagramClient
except ImportError:
    print("Error: instagrapi not installed. Run: pip install instagrapi==1.16.16")
    sys.exit(1)

try:
    from PIL import Image  # Just to check if Pillow is available
except ImportError:
    print("Error: Pillow not installed. Run: pip install pillow>=8.1.1")
    sys.exit(1)

# Bot configuration
API_ID = 7813390  # Your API I
API_HASH = "1faadd9cc60374bca1e88c2f44e3ee2f"
BOT_TOKEN = "7744174417:AAHgvYYmf2h-YkupR4gXhvqhrU7t6ItxvjE"
INSTA_USERNAME = "instantdlbottg"
INSTA_PASSWORD = "instadlbot123"
# Initialize the bot
app = Client("instagram_downloader_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

def initialize_instagram_client():
    """Initialize Instagram client with error handling"""
    ig = InstagramClient()
    try:
        if INSTA_USERNAME and INSTA_PASSWORD:
            ig.login(INSTA_USERNAME, INSTA_PASSWORD)
            print("Instagram login successful")
        return ig
    except Exception as e:
        print(f"Instagram login failed: {e}")
        return ig

ig = initialize_instagram_client()

def download_instagram_media(url: str):
    """Download Instagram media with error handling"""
    try:
        media_pk = ig.media_pk_from_url(url)
        media_info = ig.media_info(media_pk)
        
        if media_info.media_type == 2:  # Video
            download_url = media_info.video_url
            media_type = "video"
        elif media_info.media_type == 1:  # Image
            download_url = media_info.thumbnail_url
            media_type = "photo"
        elif media_info.media_type == 8:  # Album
            download_url = media_info.resources[0].thumbnail_url
            media_type = "photo"
        else:
            return None
            
        response = requests.get(download_url, stream=True)
        if response.status_code != 200:
            return None
            
        file_extension = ".mp4" if media_type == "video" else ".jpg"
        file_path = f"downloads/{media_pk}{file_extension}"
        
        os.makedirs("downloads", exist_ok=True)
        with open(file_path, "wb") as f:
            for chunk in response.iter_content(1024):
                f.write(chunk)
                
        return {
            "file_path": file_path,
            "media_type": media_type,
            "caption": media_info.caption_text or ""
        }
    except Exception as e:
        print(f"Download error: {e}")
        return None

# ... [rest of your bot code remains the same] ...

if __name__ == "__main__":
    print("Starting bot...")
    try:
        app.run()
    except Exception as e:
        print(f"Bot failed to start: {e}")
