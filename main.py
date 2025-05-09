import os
import requests
from pyrogram import Client, filters
from pyrogram.types import Message
from instagrapi import Client as InstagramClient
from config import API_ID, API_HASH, BOT_TOKEN, INSTA_USERNAME, INSTA_PASSWORD, DOWNLOAD_FOLDER

# Initialize the bot
app = Client("instagram_downloader_bot", 
             api_id=API_ID, 
             api_hash=API_HASH, 
             bot_token=BOT_TOKEN)

# Initialize Instagram client
ig = InstagramClient()
try:
    if INSTA_USERNAME and INSTA_PASSWORD:
        ig.login(INSTA_USERNAME, INSTA_PASSWORD)
except Exception as e:
    print(f"Instagram login failed: {e}")

def download_instagram_media(url: str) -> dict:
    """Download Instagram media and return media info"""
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
            
        response = requests.get(download_url)
        if response.status_code != 200:
            return None
            
        ext = ".mp4" if media_type == "video" else ".jpg"
        file_path = f"{DOWNLOAD_FOLDER}/{media_pk}{ext}"
        
        os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)
        with open(file_path, "wb") as f:
            f.write(response.content)
            
        return {
            "file_path": file_path,
            "media_type": media_type,
            "caption": media_info.caption_text or ""
        }
    except Exception as e:
        print(f"Error downloading: {e}")
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
                reply_to_message_id=message.id
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
