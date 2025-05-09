import os
import re
import requests
import time
from pyrogram import Client, filters
from pyrogram.types import Message
from urllib.parse import urlparse

# Bot configuration
API_ID = 7813390
API_HASH = "1faadd9cc60374bca1e88c2f44e3ee2f"
BOT_TOKEN = "7744174417:AAHgvYYmf2h-YkupR4gXhvqhrU7t6ItxvjE"

# Initialize the bot
app = Client("instagram_downloader_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

def clean_url(url: str) -> str:
    """Clean Instagram URL and convert to mobile version"""
    url = url.split('?')[0]  # Remove query parameters
    if 'www.instagram.com' in url:
        url = url.replace('www.instagram.com', 'm.instagram.com')
    return url

def extract_instagram_media(url: str) -> dict:
    """Improved media extractor with mobile support and better error handling"""
    try:
        url = clean_url(url)
        headers = {
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Mobile/15E148 Safari/604.1",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"
        }
        
        # Add delay to avoid rate limiting
        time.sleep(2)
        
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        html = response.text
        
        # Improved regex patterns
        video_url = re.search(r'"video_url":"(https?://[^"]+)"', html)
        image_url = re.search(r'"display_url":"(https?://[^"]+)"', html)
        
        if video_url:
            return {
                "url": video_url.group(1).replace("\\u0026", "&"),
                "type": "video",
                "source": "reel"
            }
        elif image_url:
            return {
                "url": image_url.group(1).replace("\\u0026", "&"),
                "type": "photo",
                "source": "post"
            }
        
        # Fallback to alternative extraction method
        return extract_alternative(html) or None

    except requests.exceptions.RequestException as e:
        print(f"Request failed: {str(e)}")
        return None
    except Exception as e:
        print(f"Extraction error: {str(e)}")
        return None

def extract_alternative(html: str) -> dict:
    """Alternative extraction method if primary fails"""
    try:
        # Try different patterns
        video_url = re.search(r'src="(https://[^"]+\.mp4)"', html)
        if video_url:
            return {
                "url": video_url.group(1),
                "type": "video",
                "source": "alternative"
            }
        
        image_url = re.search(r'src="(https://[^"]+\.jpg)"', html)
        if image_url:
            return {
                "url": image_url.group(1),
                "type": "photo",
                "source": "alternative"
            }
        return None
    except:
        return None

def download_media(media_url: str, media_type: str) -> str:
    """Improved downloader with timeout and chunked download"""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        
        os.makedirs("downloads", exist_ok=True)
        file_ext = ".mp4" if media_type == "video" else ".jpg"
        file_path = f"downloads/{int(time.time())}{file_ext}"
        
        with requests.get(media_url, headers=headers, stream=True, timeout=15) as r:
            r.raise_for_status()
            with open(file_path, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
        return file_path
        
    except Exception as e:
        print(f"Download failed: {str(e)}")
        if os.path.exists(file_path):
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
        "- Posts: https://instagram.com/p/...\n\n"
        "⏳ Please be patient, downloads may take 10-20 seconds"
    )

@app.on_message(filters.regex(r'https?://(www\.)?instagram\.com/(p|reel|tv)/[^/]+/?'))
async def handle_instagram_link(client: Client, message: Message):
    processing_msg = await message.reply_text("🔍 Processing your link...")
    
    try:
        media_info = extract_instagram_media(message.text)
        if not media_info:
            await processing_msg.edit_text("❌ Couldn't download. Possible reasons:\n"
                                         "1. Link is private\n"
                                         "2. Instagram changed their structure\n"
                                         "3. Server is busy\n\n"
                                         "Try again later or send a different link.")
            return

        await processing_msg.edit_text("⬇️ Downloading media...")
        file_path = download_media(media_info["url"], media_info["type"])
        
        if not file_path:
            await processing_msg.edit_text("❌ Download failed. The server may be busy.")
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
        await processing_msg.edit_text(f"⚠️ Error: {str(e)[:200]}")
    finally:
        if 'file_path' in locals() and os.path.exists(file_path):
            os.remove(file_path)

if __name__ == "__main__":
    print("Bot started! Waiting for Instagram links...")
    app.run()
