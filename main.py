import os
import re
import json
import requests
import time
from pyrogram import Client, filters
from pyrogram.types import Message
from urllib.parse import urlparse, parse_qs

# Bot configuration
API_ID = 7813390
API_HASH = "1faadd9cc60374bca1e88c2f44e3ee2f"
BOT_TOKEN = "7744174417:AAHgvYYmf2h-YkupR4gXhvqhrU7t6ItxvjE"

# Initialize the bot
app = Client("instagram_downloader_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Constants
INSTAGRAM_DOMAINS = ['instagram.com', 'www.instagram.com', 'm.instagram.com']
MAX_RETRIES = 2
REQUEST_DELAY = 3  # seconds between requests

def clean_url(url: str) -> str:
    """Clean Instagram URL and standardize format"""
    url = url.split('?')[0].rstrip('/')
    if not any(domain in url for domain in INSTAGRAM_DOMAINS):
        return None
    
    # Convert to mobile version if not already
    if 'www.instagram.com' in url:
        url = url.replace('www.instagram.com', 'm.instagram.com')
    return url

def get_shortcode(url: str) -> str:
    """Extract shortcode from Instagram URL"""
    patterns = [
        r'/reel/([^/?]+)',
        r'/p/([^/?]+)',
        r'/tv/([^/?]+)'
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None

def get_media_via_api(url: str) -> dict:
    """Try to get media using Instagram's GraphQL API"""
    try:
        shortcode = get_shortcode(url)
        if not shortcode:
            return None
            
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "X-Requested-With": "XMLHttpRequest"
        }
        
        # Try different query hashes
        query_hashes = [
            "b3055c01b4b222b8a47dc12b090e4e64",  # For reels
            "9f8827793ef34641b2fb195d4d41151c"   # For posts
        ]
        
        for query_hash in query_hashes:
            api_url = f"https://www.instagram.com/graphql/query/?query_hash={query_hash}&variables=%7B%22shortcode%22%3A%22{shortcode}%22%7D"
            
            response = requests.get(api_url, headers=headers, timeout=10)
            data = response.json()
            
            if 'data' in data and 'shortcode_media' in data['data']:
                media = data['data']['shortcode_media']
                
                if media.get('is_video'):
                    return {
                        "url": media['video_url'],
                        "type": "video",
                        "source": "api"
                    }
                else:
                    # For posts with multiple images
                    if 'edge_sidecar_to_children' in media:
                        edges = media['edge_sidecar_to_children']['edges']
                        urls = []
                        for edge in edges:
                            if edge['node']['is_video']:
                                urls.append(edge['node']['video_url'])
                            else:
                                urls.append(edge['node']['display_url'])
                        return {
                            "url": urls[0],  # Just return first media for simplicity
                            "type": "video" if any(url.endswith('.mp4') for url in urls) else "photo",
                            "source": "api",
                            "multiple": True,
                            "all_urls": urls
                        }
                    return {
                        "url": media['display_url'],
                        "type": "photo",
                        "source": "api"
                    }
        
        return None
        
    except Exception as e:
        print(f"API Error: {e}")
        return None

def get_media_via_scraping(url: str) -> dict:
    """Fallback method using HTML scraping"""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Mobile/15E148 Safari/604.1",
            "Accept-Language": "en-US,en;q=0.9"
        }
        
        time.sleep(REQUEST_DELAY)
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        html = response.text
        
        # Try different patterns
        patterns = [
            r'"video_url":"(https?://[^"]+)"',
            r'"display_url":"(https?://[^"]+)"',
            r'src="(https://[^"]+\.mp4)"',
            r'src="(https://[^"]+\.jpg)"'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, html)
            if match:
                media_url = match.group(1).replace("\\u0026", "&")
                return {
                    "url": media_url,
                    "type": "video" if '.mp4' in media_url else "photo",
                    "source": "scraping"
                }
        
        return None
        
    except Exception as e:
        print(f"Scraping Error: {e}")
        return None

def download_media(media_url: str, media_type: str) -> str:
    """Download media with retries and proper cleanup"""
    file_path = None
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        
        os.makedirs("downloads", exist_ok=True)
        file_ext = ".mp4" if media_type == "video" else ".jpg"
        file_path = f"downloads/{int(time.time())}{file_ext}"
        
        for attempt in range(MAX_RETRIES):
            try:
                with requests.get(media_url, headers=headers, stream=True, timeout=15) as r:
                    r.raise_for_status()
                    with open(file_path, 'wb') as f:
                        for chunk in r.iter_content(chunk_size=8192):
                            if chunk:
                                f.write(chunk)
                return file_path
            except Exception as e:
                if attempt == MAX_RETRIES - 1:
                    raise
                time.sleep(REQUEST_DELAY)
                
    except Exception as e:
        print(f"Download failed: {str(e)}")
        if file_path and os.path.exists(file_path):
            os.remove(file_path)
        return None

@app.on_message(filters.command(["start", "help"]))
async def start(client: Client, message: Message):
    await message.reply_text(
        "📥 Instagram Downloader Bot\n\n"
        "Send me an Instagram Reel or Post link and I'll download it for you!\n\n"
        "⚠️ Works only with public content\n"
        "🔗 Supported links:\n"
        "- Reels: https://instagram.com/reel/...\n"
        "- Posts: https://instagram.com/p/...\n"
        "- IGTV: https://instagram.com/tv/...\n\n"
        "⏳ Please be patient, downloads may take 10-20 seconds"
    )

@app.on_message(filters.regex(r'https?://(www\.)?instagram\.com/(p|reel|tv)/[^/]+/?'))
async def handle_instagram_link(client: Client, message: Message):
    processing_msg = await message.reply_text("🔍 Processing your link...")
    file_path = None
    
    try:
        url = clean_url(message.text)
        if not url:
            await processing_msg.edit_text("❌ Invalid Instagram URL. Please send a valid Reel or Post link.")
            return
        
        # Try API method first
        media_info = get_media_via_api(url)
        
        # If API fails, try scraping
        if not media_info:
            await processing_msg.edit_text("🔍 Trying alternative method...")
            media_info = get_media_via_scraping(url)
        
        if not media_info:
            await processing_msg.edit_text(
                "❌ Couldn't download this content. Possible reasons:\n"
                "1. The link is private or requires login\n"
                "2. Instagram has changed their structure\n"
                "3. The content may have been removed\n\n"
                "Try again later or send a different link."
            )
            return

        await processing_msg.edit_text(f"⬇️ Downloading media (via {media_info['source']})...")
        file_path = download_media(media_info["url"], media_info["type"])
        
        if not file_path:
            await processing_msg.edit_text("❌ Download failed. Please try again later.")
            return

        await processing_msg.edit_text("📤 Uploading to Telegram...")
        if media_info["type"] == "video":
            await client.send_video(
                chat_id=message.chat.id,
                video=file_path,
                reply_to_message_id=message.id,
                supports_streaming=True,
                progress=lambda current, total: print(f"Uploaded {current}/{total}")
            )
        else:
            await client.send_photo(
                chat_id=message.chat.id,
                photo=file_path,
                reply_to_message_id=message.id
            )
            
        await processing_msg.delete()
        
    except Exception as e:
        error_msg = str(e)[:200]
        print(f"Error: {error_msg}")
        await processing_msg.edit_text(f"⚠️ Error: {error_msg}")
    finally:
        if file_path and os.path.exists(file_path):
            os.remove(file_path)

if __name__ == "__main__":
    print("Bot started! Waiting for Instagram links...")
    app.run()
