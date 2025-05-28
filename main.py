from pyrogram import Client, filters
import yt_dlp
import os


# ---------------------------- CONFIG ----------------------------
API_ID = 7813390
API_HASH = "1faadd9cc60374bca1e88c2f44e3ee2f"
BOT_TOKEN = "7744174417:AAHgvYYmf2h-YkupR4gXhvqhrU7t6ItxvjE"

# Create downloads directory if not exists
if not os.path.exists("downloads"):
    os.makedirs("downloads")

# ---------------------------- BOT INIT ----------------------------
bot = Client("yt-dlp-bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# ---------------------------- COMMANDS ----------------------------
@bot.on_message(filters.command("start"))
async def start(_, msg):
    await msg.reply_text("Yo! 👋 Send me a YouTube link and I’ll download the video for ya 📥🔥")

@bot.on_message(filters.text & ~filters.command(["start"]))
async def download_yt(_, msg):
    url = msg.text.strip()
    if "youtube.com" not in url and "youtu.be" not in url:
        return await msg.reply_text("Brooo, that's not a YouTube link 😅")

    await msg.reply_text("📥 Downloading... Please wait ⏳")

    try:
        ydl_opts = {
            'format': 'best[ext=mp4]',
            'outtmpl': 'downloads/%(title)s.%(ext)s',
            'cookiefile': 'cookies.txt',  # use YouTube cookies for restricted videos
            'age_limit': 18
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            video_path = ydl.prepare_filename(info)

        await msg.reply_video(video_path, caption=f"🎬 {info['title']}")
        os.remove(video_path)

    except Exception as e:
        await msg.reply_text(f"❌ Error: {e}")

# ---------------------------- BOT RUN ----------------------------
bot.run()
