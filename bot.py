import os
import time
from pyrogram import Client, filters
from pyrogram.types import (
    Message,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery
)
import yt_dlp
from yt_dlp.utils import DownloadErrorimport os
import time
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
    """Extract video info without downloading"""
    ydl = yt_dlp.YoutubeDL({
        'quiet': True,
        'no_warnings': True,
        'extract_flat': True,
        'cookiefile': COOKIES_FILE if os.path.exists(COOKIES_FILE) else None
    })
    return ydl.extract_info(url, download=False)

def get_format_buttons(formats):
    """Generate quality selection buttons"""
    buttons = []
    # Filter for common video formats
    video_formats = [
        f for f in formats if 
        f.get('vcodec') != 'none' and 
        f.get('acodec') != 'none' and
        f.get('filesize') is not None
    ]
    
    # Sort by resolution then filesize
    video_formats.sort(
        key=lambda x: (
            -x.get('height', 0),
            x.get('filesize', 0)
        )
    )
    
    # Create buttons for top 5 formats
    for fmt in video_formats[:5]:
        res = fmt.get('height', '?')
        ext = fmt.get('ext', 'mp4')
        size = humanbytes(fmt.get('filesize', 0))
        buttons.append(
            [InlineKeyboardButton(
                f"🎬 {res}p ({ext.upper()}) - {size}",
                callback_data=f"dl_{fmt['format_id']}"
            )]
        )
    
    # Add audio-only option
    audio_format = next(
        (f for f in formats if 
         f.get('vcodec') == 'none' and 
         f.get('acodec') != 'none'),
        None
    )
    if audio_format:
        buttons.append(
            [InlineKeyboardButton(
                f"🔊 Audio Only ({audio_format['ext']})",
                callback_data=f"dl_{audio_format['format_id']}"
            )]
        )
    
    return InlineKeyboardMarkup(buttons)

# ---------------------------- HANDLERS ----------------------------
@bot.on_message(filters.command("start"))
async def start(_, msg: Message):
    await msg.reply_text(
        "🎥 YouTube Video Downloader\n\n"
        "Send me a YouTube link and I'll download it for you!\n\n"
        "⚡ Features:\n"
        "- Quality selection\n"
        "- Fast downloads\n"
        "- Up to 2GB files\n\n"
        "⚠️ Note: Age-restricted videos require cookies.txt",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("❓ Help", callback_data="help")]
        ])
    )

@bot.on_callback_query(filters.regex("^help$"))
async def help_callback(_, query: CallbackQuery):
    await query.message.edit_text(
        "📘 Bot Help Guide\n\n"
        "1. Send any YouTube link\n"
        "2. Select your preferred quality\n"
        "3. Wait for download to complete\n\n"
        "🔧 Troubleshooting:\n"
        "- For age-restricted videos: Use cookies.txt\n"
        "- Large videos may take time to upload\n"
        "- Try different quality if one fails",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Back", callback_data="back_to_start")]
        ])
    )

@bot.on_callback_query(filters.regex("^back_to_start$"))
async def back_to_start(_, query: CallbackQuery):
    await start(_, query.message)

@bot.on_message(filters.text & ~filters.command(["start", "help"]))
async def handle_url(_, msg: Message):
    url = msg.text.strip()
    
    if not any(x in url for x in ["youtube.com", "youtu.be"]):
        return await msg.reply_text("❌ Please send a valid YouTube URL")
    
    try:
        info = get_video_info(url)
        if not info:
            return await msg.reply_text("❌ Couldn't fetch video info. Video may be private or unavailable.")
        
        if info.get('duration', 0) > 14400:  # 4 hours
            return await msg.reply_text("❌ Video too long (max 4 hours allowed)")
        
        if 'formats' not in info:
            return await msg.reply_text("❌ Couldn't extract available formats")
        
        # Store URL in the message for callback reference
        await msg.reply_text(
            f"📹 {info.get('title', 'Untitled')}\n"
            f"⏱️ Duration: {info.get('duration_string', 'N/A')}\n\n"
            "Select download quality:",
            reply_markup=get_format_buttons(info['formats']),
            reply_to_message_id=msg.id  # This ensures reply_to_message exists
        )
        
    except Exception as e:
        await msg.reply_text(f"❌ Error: {str(e)}")

@bot.on_callback_query(filters.regex("^dl_"))
async def download_callback(_, query: CallbackQuery):
    await query.answer()
    
    try:
        # Safely get the URL from the replied message
        if not query.message.reply_to_message:
            raise ValueError("Original message not found")
            
        url = query.message.reply_to_message.text.strip()
        if not any(x in url for x in ["youtube.com", "youtu.be"]):
            raise ValueError("Invalid YouTube URL")
            
        format_id = query.data.split("_")[1]
        msg = await query.message.edit_text("📥 Starting download...")
        
        ydl_opts = {
            'format': format_id,
            'outtmpl': f'{DOWNLOAD_DIR}/%(title)s.%(ext)s',
            'cookiefile': COOKIES_FILE if os.path.exists(COOKIES_FILE) else None,
            'extractor_args': {'youtube': {'skip': ['authwall']}},
            'noplaylist': True,
            'quiet': True,
            'max_filesize': MAX_FILE_SIZE * 1024 * 1024,
            'merge_output_format': 'mp4',
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            'referer': 'https://www.youtube.com/',
            'retries': 10
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            video_path = ydl.prepare_filename(info)
            
            file_size = os.path.getsize(video_path)
            if file_size > MAX_FILE_SIZE * 1024 * 1024:
                os.remove(video_path)
                return await msg.edit_text("❌ File too large for Telegram")
            
            await msg.edit_text("📤 Uploading to Telegram...")
            await query.message.reply_video(
                video_path,
                caption=f"🎬 {info.get('title', 'Untitled')}\n"
                        f"🖥️ Quality: {format_id}\n"
                        f"📊 Size: {humanbytes(file_size)}",
                supports_streaming=True
            )
            await msg.delete()
            
    except DownloadError as e:
        await query.message.reply_text(f"❌ Download failed: {str(e)}")
    except Exception as e:
        await query.message.reply_text(f"❌ Error: {str(e)}")
    finally:
        if 'video_path' in locals() and os.path.exists(video_path):
            os.remove(video_path)

# ---------------------------- RUN BOT ----------------------------
if __name__ == "__main__":
    print("⚡ Bot is running...")
    bot.run()

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
    """Extract video info without downloading"""
    ydl = yt_dlp.YoutubeDL({
        'quiet': True,
        'no_warnings': True,
        'extract_flat': True,
        'cookiefile': COOKIES_FILE if os.path.exists(COOKIES_FILE) else None
    })
    return ydl.extract_info(url, download=False)

def get_format_buttons(formats):
    """Generate quality selection buttons"""
    buttons = []
    # Filter for common video formats
    video_formats = [
        f for f in formats if 
        f.get('vcodec') != 'none' and 
        f.get('acodec') != 'none' and
        f.get('filesize') is not None
    ]
    
    # Sort by resolution then filesize
    video_formats.sort(
        key=lambda x: (
            -x.get('height', 0),
            x.get('filesize', 0)
        )
    )
    
    # Create buttons for top 5 formats
    for fmt in video_formats[:5]:
        res = fmt.get('height', '?')
        ext = fmt.get('ext', 'mp4')
        size = humanbytes(fmt.get('filesize', 0))
        buttons.append(
            [InlineKeyboardButton(
                f"🎬 {res}p ({ext.upper()}) - {size}",
                callback_data=f"dl_{fmt['format_id']}"
            )]
        )
    
    # Add audio-only option
    audio_format = next(
        (f for f in formats if 
         f.get('vcodec') == 'none' and 
         f.get('acodec') != 'none'),
        None
    )
    if audio_format:
        buttons.append(
            [InlineKeyboardButton(
                f"🔊 Audio Only ({audio_format['ext']})",
                callback_data=f"dl_{audio_format['format_id']}"
            )]
        )
    
    return InlineKeyboardMarkup(buttons)

# ---------------------------- HANDLERS ----------------------------
@bot.on_message(filters.command("start"))
async def start(_, msg: Message):
    await msg.reply_text(
        "🎥 YouTube Video Downloader\n\n"
        "Send me a YouTube link and I'll download it for you!\n\n"
        "⚡ Features:\n"
        "- Quality selection\n"
        "- Fast downloads\n"
        "- Up to 2GB files\n\n"
        "⚠️ Note: Age-restricted videos require cookies.txt",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("❓ Help", callback_data="help")]
        ])
    )

@bot.on_callback_query(filters.regex("^help$"))
async def help_callback(_, query: CallbackQuery):
    await query.message.edit_text(
        "📘 Bot Help Guide\n\n"
        "1. Send any YouTube link\n"
        "2. Select your preferred quality\n"
        "3. Wait for download to complete\n\n"
        "🔧 Troubleshooting:\n"
        "- For age-restricted videos: Use cookies.txt\n"
        "- Large videos may take time to upload\n"
        "- Try different quality if one fails",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Back", callback_data="back_to_start")]
        ])
    )

@bot.on_callback_query(filters.regex("^back_to_start$"))
async def back_to_start(_, query: CallbackQuery):
    await start(_, query.message)

@bot.on_message(filters.text & ~filters.command(["start", "help"]))
async def handle_url(_, msg: Message):
    url = msg.text.strip()
    
    if not any(x in url for x in ["youtube.com", "youtu.be"]):
        return await msg.reply_text("❌ Please send a valid YouTube URL")
    
    try:
        info = get_video_info(url)
        if not info:
            return await msg.reply_text("❌ Couldn't fetch video info. Video may be private or unavailable.")
        
        if info.get('duration', 0) > 14400:  # 4 hours
            return await msg.reply_text("❌ Video too long (max 4 hours allowed)")
        
        if 'formats' not in info:
            return await msg.reply_text("❌ Couldn't extract available formats")
        
        # Store URL in the message for callback reference
        await msg.reply_text(
            f"📹 {info.get('title', 'Untitled')}\n"
            f"⏱️ Duration: {info.get('duration_string', 'N/A')}\n\n"
            "Select download quality:",
            reply_markup=get_format_buttons(info['formats']),
            reply_to_message_id=msg.id  # This ensures reply_to_message exists
        )
        
    except Exception as e:
        await msg.reply_text(f"❌ Error: {str(e)}")

@bot.on_callback_query(filters.regex("^dl_"))
async def download_callback(_, query: CallbackQuery):
    await query.answer()
    
    try:
        # Safely get the URL from the replied message
        if not query.message.reply_to_message:
            raise ValueError("Original message not found")
            
        url = query.message.reply_to_message.text.strip()
        if not any(x in url for x in ["youtube.com", "youtu.be"]):
            raise ValueError("Invalid YouTube URL")
            
        format_id = query.data.split("_")[1]
        msg = await query.message.edit_text("📥 Starting download...")
        
        ydl_opts = {
            'format': format_id,
            'outtmpl': f'{DOWNLOAD_DIR}/%(title)s.%(ext)s',
            'cookiefile': COOKIES_FILE if os.path.exists(COOKIES_FILE) else None,
            'extractor_args': {'youtube': {'skip': ['authwall']}},
            'noplaylist': True,
            'quiet': True,
            'max_filesize': MAX_FILE_SIZE * 1024 * 1024,
            'merge_output_format': 'mp4',
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            'referer': 'https://www.youtube.com/',
            'retries': 10
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            video_path = ydl.prepare_filename(info)
            
            file_size = os.path.getsize(video_path)
            if file_size > MAX_FILE_SIZE * 1024 * 1024:
                os.remove(video_path)
                return await msg.edit_text("❌ File too large for Telegram")
            
            await msg.edit_text("📤 Uploading to Telegram...")
            await query.message.reply_video(
                video_path,
                caption=f"🎬 {info.get('title', 'Untitled')}\n"
                        f"🖥️ Quality: {format_id}\n"
                        f"📊 Size: {humanbytes(file_size)}",
                supports_streaming=True
            )
            await msg.delete()
            
    except DownloadError as e:
        await query.message.reply_text(f"❌ Download failed: {str(e)}")
    except Exception as e:
        await query.message.reply_text(f"❌ Error: {str(e)}")
    finally:
        if 'video_path' in locals() and os.path.exists(video_path):
            os.remove(video_path)

# ---------------------------- RUN BOT ----------------------------
if __name__ == "__main__":
    print("⚡ Bot is running...")
    bot.run()import os
import time
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
    """Extract video info without downloading"""
    ydl = yt_dlp.YoutubeDL({
        'quiet': True,
        'no_warnings': True,
        'extract_flat': True,
        'cookiefile': COOKIES_FILE if os.path.exists(COOKIES_FILE) else None
    })
    return ydl.extract_info(url, download=False)

def get_format_buttons(formats):
    """Generate quality selection buttons"""
    buttons = []
    # Filter for common video formats
    video_formats = [
        f for f in formats if 
        f.get('vcodec') != 'none' and 
        f.get('acodec') != 'none' and
        f.get('filesize') is not None
    ]
    
    # Sort by resolution then filesize
    video_formats.sort(
        key=lambda x: (
            -x.get('height', 0),
            x.get('filesize', 0)
        )
    )
    
    # Create buttons for top 5 formats
    for fmt in video_formats[:5]:
        res = fmt.get('height', '?')
        ext = fmt.get('ext', 'mp4')
        size = humanbytes(fmt.get('filesize', 0))
        buttons.append(
            [InlineKeyboardButton(
                f"🎬 {res}p ({ext.upper()}) - {size}",
                callback_data=f"dl_{fmt['format_id']}"
            )]
        )
    
    # Add audio-only option
    audio_format = next(
        (f for f in formats if 
         f.get('vcodec') == 'none' and 
         f.get('acodec') != 'none'),
        None
    )
    if audio_format:
        buttons.append(
            [InlineKeyboardButton(
                f"🔊 Audio Only ({audio_format['ext']})",
                callback_data=f"dl_{audio_format['format_id']}"
            )]
        )
    
    return InlineKeyboardMarkup(buttons)

# ---------------------------- HANDLERS ----------------------------
@bot.on_message(filters.command("start"))
async def start(_, msg: Message):
    await msg.reply_text(
        "🎥 YouTube Video Downloader\n\n"
        "Send me a YouTube link and I'll download it for you!\n\n"
        "⚡ Features:\n"
        "- Quality selection\n"
        "- Fast downloads\n"
        "- Up to 2GB files\n\n"
        "⚠️ Note: Age-restricted videos require cookies.txt",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("❓ Help", callback_data="help")]
        ])
    )

@bot.on_callback_query(filters.regex("^help$"))
async def help_callback(_, query: CallbackQuery):
    await query.message.edit_text(
        "📘 Bot Help Guide\n\n"
        "1. Send any YouTube link\n"
        "2. Select your preferred quality\n"
        "3. Wait for download to complete\n\n"
        "🔧 Troubleshooting:\n"
        "- For age-restricted videos: Use cookies.txt\n"
        "- Large videos may take time to upload\n"
        "- Try different quality if one fails",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Back", callback_data="back_to_start")]
        ])
    )

@bot.on_callback_query(filters.regex("^back_to_start$"))
async def back_to_start(_, query: CallbackQuery):
    await start(_, query.message)

@bot.on_message(filters.text & ~filters.command(["start", "help"]))
async def handle_url(_, msg: Message):
    url = msg.text.strip()
    
    if not any(x in url for x in ["youtube.com", "youtu.be"]):
        return await msg.reply_text("❌ Please send a valid YouTube URL")
    
    try:
        info = get_video_info(url)
        if not info:
            return await msg.reply_text("❌ Couldn't fetch video info. Video may be private or unavailable.")
        
        if info.get('duration', 0) > 14400:  # 4 hours
            return await msg.reply_text("❌ Video too long (max 4 hours allowed)")
        
        if 'formats' not in info:
            return await msg.reply_text("❌ Couldn't extract available formats")
        
        await msg.reply_text(
            f"📹 {info.get('title', 'Untitled')}\n"
            f"⏱️ Duration: {info.get('duration_string', 'N/A')}\n\n"
            "Select download quality:",
            reply_markup=get_format_buttons(info['formats'])
        )
        
    except Exception as e:
        await msg.reply_text(f"❌ Error: {str(e)}")

@bot.on_callback_query(filters.regex("^dl_"))
async def download_callback(_, query: CallbackQuery):
    await query.answer()
    format_id = query.data.split("_")[1]
    url = query.message.reply_to_message.text.strip()
    
    msg = await query.message.reply_text("📥 Starting download...")
    
    try:
        ydl_opts = {
            'format': format_id,
            'outtmpl': f'{DOWNLOAD_DIR}/%(title)s.%(ext)s',
            'cookiefile': COOKIES_FILE if os.path.exists(COOKIES_FILE) else None,
            'extractor_args': {'youtube': {'skip': ['authwall']}},
            'noplaylist': True,
            'quiet': True,
            'max_filesize': MAX_FILE_SIZE * 1024 * 1024,
            'merge_output_format': 'mp4',
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            'referer': 'https://www.youtube.com/',
            'retries': 10
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            video_path = ydl.prepare_filename(info)
            
            file_size = os.path.getsize(video_path)
            if file_size > MAX_FILE_SIZE * 1024 * 1024:
                os.remove(video_path)
                return await msg.edit_text("❌ File too large for Telegram")
            
            await msg.edit_text("📤 Uploading to Telegram...")
            await query.message.reply_video(
                video_path,
                caption=f"🎬 {info.get('title', 'Untitled')}\n"
                        f"🖥️ Quality: {format_id}\n"
                        f"📊 Size: {humanbytes(file_size)}",
                supports_streaming=True
            )
            await msg.delete()
            
    except DownloadError as e:
        await msg.edit_text(f"❌ Download failed: {str(e)}")
    except Exception as e:
        await msg.edit_text(f"❌ Error: {str(e)}")
    finally:
        if 'video_path' in locals() and os.path.exists(video_path):
            os.remove(video_path)

# ---------------------------- RUN BOT ----------------------------
if __name__ == "__main__":
    print("⚡ Bot is running...")
    bot.run()
