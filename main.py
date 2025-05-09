import os
import re
import requests
import time
from pyrogram import Client, filters
from pyrogram.types import Message

# Bot configuration
API_ID = 7813390  # Your API I
API_HASH = "1faadd9cc60374bca1e88c2f44e3ee2f"
BOT_TOKEN = "7744174417:AAHgvYYmf2h-YkupR4gXhvqhrU7t6ItxvjE"

# Initialize the bot
app = Client("instagram_downloader_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

def extract_instagram_media(url: str) -> dict:
    """Extract direct media URL from Instagram public page"""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        
        # Get the Instagram page HTML
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            return None
            
        html = response.text
        
        # Try to find video URL first (for Reels)
        video_match = re.search(r'"video_url":"([^"]+)"', html)
        if video_match:
            return {
                "url": video_match.group(1).replace("\\u0026", "&"),
                "type": "video"
            }
        
        # Try to find image URL (for Posts)
        image_match = re.search(r'"display_url":"([^"]+)"', html)
        if image_match:
            return {
                "url": image_match.group(1).replace("\\u0026", "&"),
                "type": "photo"
            }
            
        return None
    except Exception as e:
        print(f"Error extracting media: {e}")
        return None

def download_media(media_url: str, media_type: str) -> str:
    """Download the media file and return local path"""
    try:
        response = requests.get(media_url, stream=True)
        if response.status_code != 200:
            return None
            
        # Create downloads folder if not exists
        os.makedirs("downloads", exist_ok=True)
        
        # Generate filename
        file_ext = ".mp4" if media_type == "video" else ".jpg"
        file_path = f"downloads/{int(time.time())}{file_ext}"
        
        # Save the file
        with open(file_path, "wb") as f:
            for chunk in response.iter_content(1024):
                f.write(chunk)
                
        return file_path
    except Exception as e:
        print(f"Error downloading media: {e}")
        return None

@app.on_message(filters.command(["start", "help"]))
async def start(client: Client, message: Message):
    await message.reply_text(
        "📥 Instagram Downloader Bot\n\n"
        "Send me an Instagram Reel or Post link and I'll download it for you!\n\n"
        "⚠️ Works only with public content\n"
        "🔗 Supported links:\n"
        "- Reels: https://instagram.com/reel/...\n"
        "- Posts: https://instagram.com/p/..."
    )

@app.on_message(filters.regex(r'https?://(www\.)?instagram\.com/(p|reel)/[^/]+/?'))
async def handle_instagram_link(client: Client, message: Message):
    # Send processing message
    processing_msg = await message.reply_text("⬇️ Downloading... Please wait...")
    
    # Extract media URL from Instagram page
    media_info = extract_instagram_media(message.text)
    if not media_info:
        await processing_msg.edit_text("❌ Couldn't extract media. Link may be invalid or private.")
        return
    
    # Download the media file
    file_path = download_media(media_info["url"], media_info["type"])
    if not file_path:
        await processing_msg.edit_text("❌ Failed to download the media.")
        return
    
    try:
        # Send the media back to user
        if media_info["type"] == "video":
            await client.send_video(
                chat_id=message.chat.id,
                video=file_path,
                reply_to_message_id=message.id,
                supports_streaming=True
            )
        else:
            await client.send_photo(
                chat_id=message.chat.id,
                photo=file_path,
                reply_to_message_id=message.id
            )
        
        # Delete processing message
        await processing_msg.delete()
        
    except Exception as e:
        await processing_msg.edit_text(f"⚠️ Error: {str(e)}")
    
    # Clean up downloaded file
    try:
        os.remove(file_path)
    except:
        pass

if __name__ == "__main__":
    print("Bot started! Waiting for Instagram links...")
    app.run()
