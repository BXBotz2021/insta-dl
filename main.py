import os
import requests
from pyrogram import Client, filters
from pyrogram.types import Message
from typing import Dict, Optional  # For Python 3.8 compatibility
from instagrapi import Client as InstagramClient

# Bot configuration
API_ID = 7813390  # Your API I
API_HASH = "1faadd9cc60374bca1e88c2f44e3ee2f"
BOT_TOKEN = "7744174417:AAHgvYYmf2h-YkupR4gXhvqhrU7t6ItxvjE"
INSTA_USERNAME = "instantdlbottg"
INSTA_PASSWORD = "instadlbot123"

# Initialize the bot
app = Client("instagram_downloader_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Initialize Instagram client
ig = InstagramClient()
try:
    if INSTA_USERNAME and INSTA_PASSWORD:
        ig.login(INSTA_USERNAME, INSTA_PASSWORD)
except Exception as e:
    print(f"Instagram login failed: {e}")

def download_instagram_media(url: str) -> Optional[Dict]:
    """Download Instagram media (reels, posts) and return media info"""
    try:
        media_pk = ig.media_pk_from_url(url)
        media_info = ig.media_info(media_pk)
        
        # Get the appropriate URL based on media type
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
            
        # Download the media
        response = requests.get(download_url)
        if response.status_code != 200:
            return None
            
        file_extension = ".mp4" if media_type == "video" else ".jpg"
        file_path = f"downloads/{media_pk}{file_extension}"
        
        os.makedirs("downloads", exist_ok=True)
        with open(file_path, "wb") as f:
            f.write(response.content)
            
        return {
            "file_path": file_path,
            "media_type": media_type,
            "caption": media_info.caption_text if media_info.caption_text else ""
        }
        
    except Exception as e:
        print(f"Error downloading Instagram media: {e}")
        return None

@app.on_message(filters.command(["start", "help"]))
async def start(client: Client, message: Message):
    await message.reply_text(
        "📥 Instagram Downloader Bot\n\n"
        "Send me an Instagram Reel or Post link and I'll download it for you!\n\n"
        "Supported links:\n"
        "- Reels: https://instagram.com/reel/...\n"
        "- Posts: https://instagram.com/p/..."
    )

@app.on_message(filters.regex(r'https?://(www\.)?instagram\.com/(p|reel)/[^/]+/?'))
async def handle_instagram_link(client: Client, message: Message):
    processing_msg = await message.reply_text("⬇️ Downloading...")
    
    media_info = download_instagram_media(message.text)
    
    if not media_info:
        await processing_msg.edit_text("❌ Failed to download. Please check the link and try again.")
        return
    
    try:
        if media_info["media_type"] == "video":
            await client.send_video(
                chat_id=message.chat.id,
                video=media_info["file_path"],
                caption=media_info["caption"],
                reply_to_message_id=message.id,
                supports_streaming=True
            )
        else:
            await client.send_photo(
                chat_id=message.chat.id,
                photo=media_info["file_path"],
                caption=media_info["caption"],
                reply_to_message_id=message.id
            )
        await processing_msg.delete()
    except Exception as e:
        await processing_msg.edit_text(f"⚠️ Error: {str(e)}")
    finally:
        try:
            os.remove(media_info["file_path"])
        except:
            pass

if __name__ == "__main__":
    print("Bot is running...")
    app.run()
