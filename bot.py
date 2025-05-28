import os
import time
import random
from pyrogram import Client, filters
from pyrogram.types import (
    Message,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery
)
import yt_dlp
from yt_dlp.utils import DownloadError

# ---------------------------- CONFIG ----------------------------
API_ID = 7813390  # Replace with your API_ID
API_HASH = "1faadd9cc60374bca1e88c2f44e3ee2f"  # Replace with your API_HASH
BOT_TOKEN = "8132280304:AAHK129IwpEdLgHH1ORN4DbeHazBd0mtkE0"  # Replace with your bot token

MAX_FILE_SIZE = 2000  # 2GB in MB (Telegram limit)
COOKIES_FILE = "cookies.txt"  # Path to cookies file
DOWNLOAD_DIR = "downloads"

os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# ---------------------------- BOT INIT ----------------------------
bot = Client("yt-dlp-bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# ---------------------------- UTILS ----------------------------
def humanbytes(size):
    """Convert bytes to human-readable format"""
    units = ["B", "KB", "MB", "GB", "TB"]
    size = float(size)
    i = 0
    while size >= 1024 and i < len(units)-1:
        size /= 1024
        i += 1
    return f"{size:.2f} {units[i]}"

def get_video_info(url):
    """Extract video info with enhanced options"""
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'extract_flat': True,
        'cookiefile': COOKIES_FILE if os.path.exists(COOKIES_FILE) else None,
        'format': 'best',
        'nocheckcertificate': True,
        'ignoreerrors': False,
        'no_color': True,
        'noprogress': True,
        'allow_unplayable_formats': False,
        'extractor_args': {
            'youtube': {
                'skip': ['dash', 'hls'],
                'player_skip': ['js', 'configs', 'webpage']
            }
        },
        'socket_timeout': 30,
        'retries': 5,
        'user_agent': get_random_user_agent(),
        'referer': 'https://www.youtube.com/'
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            return ydl.extract_info(url, download=False)
    except Exception as e:
        print(f"Error extracting info: {str(e)}")
        return None

def get_random_user_agent():
    """Rotate user agents to avoid throttling"""
    agents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/115.0',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36'
    ]
    return random.choice(agents)

def get_format_buttons(formats):
    """Generate quality selection buttons with improved format filtering"""
    buttons = []
    
    # Filter and sort formats
    video_formats = []
    for f in formats:
        if not f.get('vcodec') or f['vcodec'] == 'none':
            continue
        
        # Skip formats without audio
        if not f.get('acodec') or f['acodec'] == 'none':
            continue
            
        # Skip formats that are too large
        if f.get('filesize', 0) > MAX_FILE_SIZE * 1024 * 1024:
            continue
            
        video_formats.append(f)
    
    # Sort by quality (height) and filesize
    video_formats.sort(key=lambda x: (-x.get('height', 0), x.get('filesize', 0)))
    
    # Add video format buttons
    added_resolutions = set()
    for fmt in video_formats:
        res = fmt.get('height', '?')
        
        # Skip duplicate resolutions
        if res in added_resolutions:
            continue
            
        added_resolutions.add(res)
        ext = fmt.get('ext', 'mp4')
        size = humanbytes(fmt.get('filesize', 0))
        
        buttons.append([
            InlineKeyboardButton(
                f"🎬 {res}p ({ext.upper()}) - {size}",
                callback_data=f"dl_{fmt['format_id']}"
            )
        ])
        
        # Limit to top 4 quality options
        if len(buttons) >= 4:
            break
    
    # Add audio-only option
    audio_formats = [f for f in formats if f.get('vcodec') == 'none' and f.get('acodec') != 'none']
    if audio_formats:
        best_audio = max(audio_formats, key=lambda x: x.get('abr', 0))
        buttons.append([
            InlineKeyboardButton(
                f"🔊 Audio Only ({best_audio['ext']}) - {humanbytes(best_audio.get('filesize', 0))}",
                callback_data=f"dl_{best_audio['format_id']}"
            )
        ])
    
    return InlineKeyboardMarkup(buttons)

# ---------------------------- HANDLERS ----------------------------
@bot.on_message(filters.command("start"))
async def start(_, msg: Message):
    await msg.reply_text(
        "🎥 YouTube Video Downloader\n\n"
        "Send me a YouTube link and I'll download it for you!\n\n"
        "⚡ Features:\n"
        "- Multiple quality options\n"
        "- Fast downloads\n"
        "- Up to 2GB files\n"
        "- Audio extraction\n\n"
        "⚠️ Note: Some videos may require cookies.txt for age-restricted content",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("❓ Help", callback_data="help")]
        ])
    )

@bot.on_message(filters.regex(r'(https?://)?(www\.)?(youtube\.com/watch\?v=|youtu\.be/|youtube\.com/shorts/)[\w-]+'))
async def youtube_link_handler(_, message: Message):
    """Handle YouTube video links"""
    try:
        url = message.text.strip()
        status_msg = await message.reply_text("🔍 Fetching video information...")
        
        info = get_video_info(url)
        if not info:
            return await status_msg.edit_text("❌ Failed to fetch video information. Please check the URL and try again.")
        
        title = info.get('title', 'Video')
        duration = info.get('duration')
        uploader = info.get('uploader', 'Unknown')
        
        formats = info.get('formats', [])
        if not formats:
            return await status_msg.edit_text("❌ No downloadable formats found for this video.")
        
        await status_msg.edit_text(
            f"🎬 {title}\n"
            f"👤 {uploader}\n"
            f"⏱️ Duration: {time.strftime('%H:%M:%S', time.gmtime(duration)) if duration else 'Unknown'}\n\n"
            "Select video quality:",
            reply_markup=get_format_buttons(formats)
        )
    except Exception as e:
        await message.reply_text(f"❌ Error: {str(e)}")

@bot.on_callback_query(filters.regex("^help$"))
async def help_callback(_, query: CallbackQuery):
    """Handle help button callback"""
    await query.answer()
    await query.message.edit_text(
        "📖 Help & Instructions\n\n"
        "1️⃣ Send a YouTube video link\n"
        "2️⃣ Bot will show available qualities\n"
        "3️⃣ Select your preferred quality\n"
        "4️⃣ Wait for download & upload\n\n"
        "📝 Supported Links:\n"
        "• Regular YouTube videos\n"
        "• YouTube Shorts\n"
        "• Age-restricted videos (requires cookies.txt)\n\n"
        "⚠️ Limitations:\n"
        "• Max file size: 2GB\n"
        "• One video at a time\n"
        "• No playlists\n\n"
        "❓ Having issues? Try:\n"
        "• Check if video is public\n"
        "• Try different quality\n"
        "• For age-restricted videos, provide cookies.txt",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Back", callback_data="back_to_start")]
        ])
    )

@bot.on_callback_query(filters.regex("^back_to_start$"))
async def back_to_start(_, query: CallbackQuery):
    """Handle back button to return to start message"""
    await query.answer()
    await query.message.edit_text(
        "🎥 YouTube Video Downloader\n\n"
        "Send me a YouTube link and I'll download it for you!\n\n"
        "⚡ Features:\n"
        "- Multiple quality options\n"
        "- Fast downloads\n"
        "- Up to 2GB files\n"
        "- Audio extraction\n\n"
        "⚠️ Note: Some videos may require cookies.txt for age-restricted content",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("❓ Help", callback_data="help")]
        ])
    )

@bot.on_callback_query(filters.regex("^dl_"))
async def download_callback(_, query: CallbackQuery):
    await query.answer()
    
    try:
        if not query.message.reply_to_message:
            raise ValueError("Original message not found")
            
        url = query.message.reply_to_message.text.strip()
        if not any(x in url for x in ["youtube.com", "youtu.be"]):
            raise ValueError("Invalid YouTube URL")
            
        format_id = query.data.split("_")[1]
        status_msg = await query.message.edit_text("📥 Initializing download...")
        
        ydl_opts = {
            'format': format_id,
            'outtmpl': f'{DOWNLOAD_DIR}/%(title)s.%(ext)s',
            'cookiefile': COOKIES_FILE if os.path.exists(COOKIES_FILE) else None,
            'nocheckcertificate': True,
            'ignoreerrors': False,
            'no_color': True,
            'noprogress': True,
            'noplaylist': True,
            'max_filesize': MAX_FILE_SIZE * 1024 * 1024,
            'merge_output_format': 'mp4',
            'socket_timeout': 30,
            'retries': 5,
            'fragment_retries': 5,
            'extractor_retries': 5,
            'user_agent': get_random_user_agent(),
            'referer': 'https://www.youtube.com/',
            'extractor_args': {
                'youtube': {
                    'skip': ['dash', 'hls'],
                    'player_skip': ['js', 'configs', 'webpage']
                }
            },
            'progress_hooks': [
                lambda d: handle_progress(d, status_msg) if d['status'] == 'downloading' else None
            ]
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            video_path = ydl.prepare_filename(info)
            
            if not os.path.exists(video_path):
                raise ValueError("Download failed - file not found")
            
            file_size = os.path.getsize(video_path)
            if file_size > MAX_FILE_SIZE * 1024 * 1024:
                os.remove(video_path)
                return await status_msg.edit_text("❌ File too large for Telegram (max 2GB)")
            
            await status_msg.edit_text("📤 Uploading to Telegram...")
            
            duration = info.get('duration')
            thumb = None
            if info.get('thumbnail'):
                try:
                    thumb = await bot.download_media(info['thumbnail'])
                except:
                    pass
            
            await query.message.reply_video(
                video_path,
                caption=f"🎬 {info.get('title', 'Video')}\n"
                        f"👤 {info.get('uploader', 'Unknown')}\n"
                        f"⚡ Quality: {info.get('format_note', format_id)}\n"
                        f"📊 Size: {humanbytes(file_size)}",
                duration=duration,
                thumb=thumb,
                supports_streaming=True
            )
            
            await status_msg.delete()
            
            # Cleanup
            if thumb:
                try:
                    os.remove(thumb)
                except:
                    pass
            
    except DownloadError as e:
        error_msg = str(e)
        if "Video unavailable" in error_msg:
            await status_msg.edit_text("❌ This video is unavailable or private")
        elif "Sign in" in error_msg:
            await status_msg.edit_text(
                "❌ This video requires authentication\n\n"
                "Please provide a valid cookies.txt file"
            )
        else:
            await status_msg.edit_text(
                "❌ Download failed\n\n"
                "Possible reasons:\n"
                "• Video is age-restricted (need cookies.txt)\n"
                "• Video is private/unavailable\n"
                "• Network error\n\n"
                "Try another quality option or check if the video is accessible"
            )
    except Exception as e:
        await status_msg.edit_text(f"❌ Error: {str(e)}")
    finally:
        if 'video_path' in locals() and os.path.exists(video_path):
            try:
                os.remove(video_path)
            except:
                pass

async def handle_progress(d, status_msg):
    """Handle download progress updates"""
    try:
        total = d.get('total_bytes', 0) or d.get('total_bytes_estimate', 0)
        downloaded = d.get('downloaded_bytes', 0)
        
        if total > 0:
            percentage = (downloaded / total) * 100
            speed = d.get('speed', 0)
            if speed:
                eta = (total - downloaded) / speed
                await status_msg.edit_text(
                    f"📥 Downloading: {percentage:.1f}%\n"
                    f"⚡ Speed: {humanbytes(speed)}/s\n"
                    f"⏱️ ETA: {time.strftime('%M:%S', time.gmtime(eta))}"
                )
    except:
        pass  # Ignore progress update errors

# ---------------------------- RUN BOT ----------------------------
if __name__ == "__main__":
    print("⚡ Bot is running with enhanced download capabilities...")
    bot.run()
