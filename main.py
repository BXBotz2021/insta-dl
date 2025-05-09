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
    """Alternative downloader without login"""
    try:
        # Use direct scraping approach
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36..."
        }
        response = requests.get(f"https://instagram.com/p/{url.split('/')[-2]}", headers=headers)
        
        # Extract video/image URL from HTML
        if 'video_url' in response.text:
            media_url = re.search('"video_url":"([^"]+)"', response.text).group(1)
            media_type = "video"
        else:
            media_url = re.search('"display_url":"([^"]+)"', response.text).group(1)
            media_type = "photo"
            
        # Download the media
        file_path = f"downloads/{int(time.time())}.{'mp4' if media_type == 'video' else 'jpg'}"
        # ... rest of download code ...
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
