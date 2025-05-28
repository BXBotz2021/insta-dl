import os
import time
from pyrogram import Client, filters
from pyrogram.types import Message
import yt_dlp
from yt_dlp.utils import DownloadError

# ---------------------------- CONFIG ----------------------------
API_ID = 7813390  # Replace with your API_ID
API_HASH = "1faadd9cc60374bca1e88c2f44e3ee2f"  # Replace with your API_HASH
BOT_TOKEN = "7744174417:AAHgvYYmf2h-YkupR4gXhvqhrU7t6ItxvjE"  # Replace with your bot token

MAX_FILE_SIZE = 2000  # 2GB in MB (Telegram limit)
COOKIES_FILE = "cookies.txt"  # Make sure this exists in your bot's directory

# Create downloads directory if not exists
os.makedirs("downloads", exist_ok=True)

# ---------------------------- BOT INIT ----------------------------
bot = Client("yt-dlp-bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# ---------------------------- UTILS ----------------------------
def humanbytes(size: float) -> str:
    """Convert bytes to human-readable format"""
    units = ["B", "KB", "MB", "GB", "TB"]
    size = float(size)
    i = 0
    while size >= 1024 and i < len(units)-1:
        size /= 1024
        i += 1
    return f"{size:.2f} {units[i]}"

class DownloadProgress:
    def __init__(self, message: Message):
        self.message = message
        self.last_update = 0

    async def progress_hook(self, d):
        if d['status'] == 'downloading':
            now = time.time()
            if now - self.last_update > 5:  # Update every 5 seconds
                self.last_update = now
                percent = d.get('_percent_str', "N/A")
                speed = d.get('_speed_str', "N/A")
                eta = d.get('_eta_str', "N/A")
                await self.message.edit_text(
                    f"📥 Downloading...\n"
                    f"⏳ Progress: {percent}\n"
                    f"🚀 Speed: {speed}\n"
                    f"⏱️ ETA: {eta}"
                )

# ---------------------------- COMMANDS ----------------------------
@bot.on_message(filters.command("start"))
async def start(_, msg: Message):
    await msg.reply_text(
        "🔥 YouTube Video Downloader Bot\n\n"
        "Send me a YouTube link and I'll download it for you!\n\n"
        "⚠️ Max video size: 2GB\n"
        "⏳ Max duration: 4 hours"
    )

@bot.on_message(filters.command("help"))
async def help(_, msg: Message):
    await msg.reply_text(
        "How to use this bot:\n\n"
        "1. Send any YouTube link (video/shorts/playlist)\n"
        "2. Wait for download to complete\n"
        "3. Receive the video in Telegram\n\n"
        "❓ Issues? Try again later or use a different video."
    )

@bot.on_message(filters.text & ~filters.command(["start", "help"]))
async def download_yt(_, msg: Message):
    url = msg.text.strip()
    
    # Validate URL
    if not any(x in url for x in ["youtube.com", "youtu.be"]):
        return await msg.reply_text("❌ Invalid YouTube URL. Please send a valid link.")
    
    status_msg = await msg.reply_text("🔍 Checking video...")
    
    try:
        # First check if video is available
        ydl_info = yt_dlp.YoutubeDL({
            'quiet': True,
            'no_warnings': True,
            'extract_flat': True,
            'cookiefile': COOKIES_FILE if os.path.exists(COOKIES_FILE) else None
        })
        
        info = ydl_info.extract_info(url, download=False)
        if not info:
            return await status_msg.edit_text("❌ Video unavailable (private/age-restricted/deleted)")

        # Check duration (max 4 hours)
        if info.get('duration', 0) > 14400:
            return await status_msg.edit_text("❌ Video too long (max 4 hours allowed)")

        await status_msg.edit_text("📥 Starting download...")
        
        # Setup progress hook
        progress = DownloadProgress(status_msg)
        
        # Download options
        ydl_opts = {
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
            'outtmpl': 'downloads/%(title)s.%(ext)s',
            'progress_hooks': [progress.progress_hook],
            'cookiefile': COOKIES_FILE if os.path.exists(COOKIES_FILE) else None,
            'extractor_args': {'youtube': {'skip': ['authwall']}},
            'noplaylist': True,
            'quiet': True,
            'max_filesize': MAX_FILE_SIZE * 1024 * 1024,
            'merge_output_format': 'mp4',
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            video_path = ydl.prepare_filename(info)
            
            # Verify download
            if not os.path.exists(video_path):
                return await status_msg.edit_text("❌ Download failed (file not created)")
            
            file_size = os.path.getsize(video_path)
            if file_size > MAX_FILE_SIZE * 1024 * 1024:
                os.remove(video_path)
                return await status_msg.edit_text(f"❌ File too large ({humanbytes(file_size)} > {MAX_FILE_SIZE}MB limit)")

            await status_msg.edit_text("📤 Uploading to Telegram...")
            await msg.reply_video(
                video_path,
                caption=f"🎬 {info.get('title', 'Untitled')}\n"
                       f"🕒 Duration: {info.get('duration_string', 'N/A')}\n"
                       f"📊 Size: {humanbytes(file_size)}",
                supports_streaming=True,
                progress=progress.progress_hook
            )
            await status_msg.delete()
            
    except DownloadError as e:
        if "Sign in to confirm" in str(e):
            await status_msg.edit_text("🔒 YouTube requires CAPTCHA verification\n\nTry again later or use different video")
        else:
            await status_msg.edit_text(f"❌ Download Error: {str(e)}")
    except Exception as e:
        await status_msg.edit_text(f"❌ Unexpected Error: {str(e)}")
    finally:
        if 'video_path' in locals() and os.path.exists(video_path):
            os.remove(video_path)

# ---------------------------- BOT RUN ----------------------------
if __name__ == "__main__":
    print("✅ Bot is running...")
    bot.run()
