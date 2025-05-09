import os
import re
import json
import requests
import time
import logging
from urllib.parse import urlparse, parse_qs
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Bot configuration
API_ID = 7813390
API_HASH = "1faadd9cc60374bca1e88c2f44e3ee2f"
BOT_TOKEN = "7744174417:AAHgvYYmf2h-YkupR4gXhvqhrU7t6ItxvjE"

# Instagram configuration
INSTAGRAM_DOMAINS = [
    'instagram.com', 
    'www.instagram.com', 
    'm.instagram.com',
    'instagram.com',
    'instagr.am'
]
MAX_RETRIES = 3
REQUEST_DELAY = 2  # seconds between requests
DOWNLOAD_TIMEOUT = 30  # seconds
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 16_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Linux; Android 10; SM-G975F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.120 Mobile Safari/537.36"
]

# Initialize the bot
app = Client(
    "instagram_downloader_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

class InstagramMediaDownloader:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "Accept-Language": "en-US,en;q=0.9",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"
        })

    def clean_url(self, url: str) -> str:
        """Standardize Instagram URL format"""
        if not url:
            return None
            
        url = url.strip().split('?')[0].rstrip('/')
        
        # Validate domain
        if not any(domain in url for domain in INSTAGRAM_DOMAINS):
            return None
            
        # Convert to mobile version
        if 'www.instagram.com' in url:
            url = url.replace('www.instagram.com', 'm.instagram.com')
        elif 'instagram.com' in url and not url.startswith('https://m.'):
            url = url.replace('instagram.com', 'm.instagram.com')
            
        # Ensure HTTPS
        if not url.startswith('https://'):
            url = url.replace('http://', 'https://')
            
        return url

    def get_shortcode(self, url: str) -> str:
        """Extract Instagram shortcode from URL"""
        patterns = [
            r'/reel/([^/?]+)',
            r'/p/([^/?]+)',
            r'/tv/([^/?]+)',
            r'/([^/?]+)/?$'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None

    def get_media_via_oembed(self, url: str) -> dict:
        """Try Instagram oEmbed API"""
        try:
            oembed_url = f"https://api.instagram.com/oembed/?url={url}"
            response = self.session.get(
                oembed_url,
                headers={"User-Agent": USER_AGENTS[0]},
                timeout=10
            )
            data = response.json()
            
            if 'thumbnail_url' in data:
                return {
                    "url": data['thumbnail_url'],
                    "type": "photo",
                    "source": "oembed"
                }
        except Exception as e:
            logger.warning(f"oEmbed failed: {str(e)}")
        return None

    def get_media_via_graphql(self, url: str) -> dict:
        """Use Instagram GraphQL API"""
        try:
            shortcode = self.get_shortcode(url)
            if not shortcode:
                return None
                
            headers = {
                "User-Agent": USER_AGENTS[0],
                "X-Requested-With": "XMLHttpRequest",
                "Referer": "https://www.instagram.com/"
            }
            
            # Try multiple query hashes
            query_hashes = [
                ("b3055c01b4b222b8a47dc12b090e4e64", "reels"),  # Reels
                ("9f8827793ef34641b2fb195d4d41151c", "posts"),  # Posts
                ("2b0673e0dc4580674a88d426fe00ea90", "stories") # Stories
            ]
            
            for query_hash, _ in query_hashes:
                api_url = (
                    f"https://www.instagram.com/graphql/query/"
                    f"?query_hash={query_hash}"
                    f"&variables=%7B%22shortcode%22%3A%22{shortcode}%22%7D"
                )
                
                response = self.session.get(
                    api_url,
                    headers=headers,
                    timeout=10
                )
                data = response.json()
                
                if 'data' not in data or 'shortcode_media' not in data['data']:
                    continue
                    
                media = data['data']['shortcode_media']
                
                # Handle videos
                if media.get('is_video'):
                    return {
                        "url": media['video_url'],
                        "type": "video",
                        "source": "graphql"
                    }
                
                # Handle single image posts
                if 'display_url' in media:
                    return {
                        "url": media['display_url'],
                        "type": "photo",
                        "source": "graphql"
                    }
                
                # Handle carousel posts
                if 'edge_sidecar_to_children' in media:
                    edges = media['edge_sidecar_to_children']['edges']
                    media_items = []
                    
                    for edge in edges:
                        node = edge['node']
                        if node.get('is_video'):
                            media_items.append({
                                "url": node['video_url'],
                                "type": "video"
                            })
                        else:
                            media_items.append({
                                "url": node['display_url'],
                                "type": "photo"
                            })
                    
                    if media_items:
                        return {
                            "url": media_items[0]['url'],
                            "type": media_items[0]['type'],
                            "source": "graphql",
                            "all_media": media_items
                        }
        
        except Exception as e:
            logger.error(f"GraphQL API error: {str(e)}")
        return None

    def get_media_via_scraping(self, url: str) -> dict:
        """Fallback to HTML scraping"""
        try:
            headers = {
                "User-Agent": USER_AGENTS[1],
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"
            }
            
            time.sleep(REQUEST_DELAY)
            response = self.session.get(
                url,
                headers=headers,
                timeout=10
            )
            response.raise_for_status()
            html = response.text
            
            # Try multiple extraction patterns
            patterns = [
                # Video URLs
                r'"video_url":"([^"]+)"',
                r'src="(https://[^"]+\.mp4)"',
                r'content="(https://[^"]+\.mp4)"',
                
                # Image URLs
                r'"display_url":"([^"]+)"',
                r'src="(https://[^"]+\.jpg)"',
                r'content="(https://[^"]+\.jpg)"',
                r'property="og:image" content="([^"]+)"'
            ]
            
            for pattern in patterns:
                matches = re.findall(pattern, html)
                for match in matches:
                    if match and ('instagram.com' in match or 'cdninstagram.com' in match):
                        media_url = match.replace("\\u0026", "&")
                        return {
                            "url": media_url,
                            "type": "video" if '.mp4' in media_url else "photo",
                            "source": "scraping"
                        }
        
        except Exception as e:
            logger.error(f"Scraping error: {str(e)}")
        return None

    def get_media_via_private_api(self, url: str) -> dict:
        """Alternative private API method"""
        try:
            shortcode = self.get_shortcode(url)
            if not shortcode:
                return None
                
            api_url = f"https://www.instagram.com/p/{shortcode}/?__a=1"
            
            headers = {
                "User-Agent": USER_AGENTS[2],
                "X-Requested-With": "XMLHttpRequest"
            }
            
            response = self.session.get(
                api_url,
                headers=headers,
                timeout=10
            )
            data = response.json()
            
            if 'graphql' in data and 'shortcode_media' in data['graphql']:
                media = data['graphql']['shortcode_media']
                
                if media.get('is_video'):
                    return {
                        "url": media['video_url'],
                        "type": "video",
                        "source": "private_api"
                    }
                else:
                    return {
                        "url": media['display_url'],
                        "type": "photo",
                        "source": "private_api"
                    }
        
        except Exception as e:
            logger.warning(f"Private API failed: {str(e)}")
        return None

    def download_media(self, media_url: str, media_type: str) -> str:
        """Download media with retries and proper cleanup"""
        if not media_url:
            return None
            
        file_path = None
        temp_files = []
        
        try:
            os.makedirs("downloads", exist_ok=True)
            file_ext = ".mp4" if media_type == "video" else ".jpg"
            file_path = f"downloads/{int(time.time())}_{os.urandom(4).hex()}{file_ext}"
            temp_files.append(file_path)
            
            headers = {
                "User-Agent": USER_AGENTS[0],
                "Referer": "https://www.instagram.com/"
            }
            
            for attempt in range(MAX_RETRIES):
                try:
                    with self.session.get(
                        media_url,
                        headers=headers,
                        stream=True,
                        timeout=DOWNLOAD_TIMEOUT
                    ) as response:
                        response.raise_for_status()
                        
                        with open(file_path, 'wb') as f:
                            for chunk in response.iter_content(chunk_size=8192):
                                if chunk:
                                    f.write(chunk)
                    
                    # Verify downloaded file
                    if os.path.getsize(file_path) > 1024:  # At least 1KB
                        return file_path
                    else:
                        os.remove(file_path)
                        raise Exception("Empty file downloaded")
                        
                except Exception as e:
                    if attempt == MAX_RETRIES - 1:
                        raise
                    time.sleep(REQUEST_DELAY)
        
        except Exception as e:
            logger.error(f"Download failed: {str(e)}")
            for temp_file in temp_files:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
            return None
        
        finally:
            # Clean up any remaining temp files
            for temp_file in temp_files:
                if temp_file != file_path and os.path.exists(temp_file):
                    os.remove(temp_file)
                    
        return file_path

# Initialize downloader
downloader = InstagramMediaDownloader()

@app.on_message(filters.command(["start", "help"]))
async def start_command(client: Client, message: Message):
    help_text = (
        "📥 **Instagram Media Downloader Bot**\n\n"
        "Send me an Instagram link and I'll download the media for you!\n\n"
        "🔗 **Supported Links**:\n"
        "- Posts: `https://www.instagram.com/p/ABC123/`\n"
        "- Reels: `https://www.instagram.com/reel/XYZ456/`\n"
        "- Stories: `https://www.instagram.com/stories/username/123456/`\n\n"
        "⚙️ **Features**:\n"
        "- Download videos and photos\n"
        "- Multiple extraction methods\n"
        "- Automatic quality selection\n\n"
        "⚠️ **Note**: Only works with public content"
    )
    
    await message.reply_text(
        help_text,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Report Issue", url="https://t.me/yourchannel")]
        ])
    )

@app.on_message(filters.regex(
    r'https?://(www\.)?(instagram\.com|instagr\.am)/(p|reel|tv|stories)/[^/]+/?'
))
async def handle_instagram_link(client: Client, message: Message):
    processing_msg = await message.reply_text("🔍 Processing your link...")
    file_path = None
    
    try:
        # Clean and validate URL
        url = downloader.clean_url(message.text)
        if not url:
            await processing_msg.edit_text("❌ Invalid Instagram URL. Please send a valid link.")
            return
        
        # Try multiple extraction methods
        extraction_methods = [
            ("GraphQL API", downloader.get_media_via_graphql),
            ("Private API", downloader.get_media_via_private_api),
            ("oEmbed", downloader.get_media_via_oembed),
            ("Scraping", downloader.get_media_via_scraping)
        ]
        
        media_info = None
        for method_name, method_func in extraction_methods:
            await processing_msg.edit_text(f"🔍 Trying {method_name}...")
            media_info = method_func(url)
            if media_info:
                logger.info(f"Success with {method_name}")
                break
            time.sleep(REQUEST_DELAY)
        
        if not media_info:
            await processing_msg.edit_text(
                "❌ Couldn't download this content. Possible reasons:\n\n"
                "1. The link is private or requires login\n"
                "2. Instagram has changed their API/structure\n"
                "3. The content may have been removed\n"
                "4. Rate limiting from Instagram\n\n"
                "Try again later or send a different link."
            )
            return
        
        # Download media
        await processing_msg.edit_text(f"⬇️ Downloading {media_info['type']}...")
        file_path = downloader.download_media(media_info['url'], media_info['type'])
        
        if not file_path:
            await processing_msg.edit_text("❌ Download failed. Please try again later.")
            return
        
        # Upload to Telegram
        await processing_msg.edit_text("📤 Uploading to Telegram...")
        
        upload_start = time.time()
        if media_info['type'] == "video":
            await client.send_video(
                chat_id=message.chat.id,
                video=file_path,
                caption=f"Source: {media_info['source']}",
                reply_to_message_id=message.id,
                supports_streaming=True,
                progress=lambda current, total: logger.info(
                    f"Upload progress: {current}/{total} bytes"
                )
            )
        else:
            await client.send_photo(
                chat_id=message.chat.id,
                photo=file_path,
                caption=f"Source: {media_info['source']}",
                reply_to_message_id=message.id
            )
        
        upload_time = time.time() - upload_start
        logger.info(f"Upload completed in {upload_time:.2f} seconds")
        
        await processing_msg.delete()
        
    except Exception as e:
        error_msg = str(e)[:200]
        logger.error(f"Error processing {url}: {error_msg}")
        await processing_msg.edit_text(
            f"⚠️ An error occurred:\n\n{error_msg}\n\n"
            "Please try again later or report this issue."
        )
        
    finally:
        if file_path and os.path.exists(file_path):
            os.remove(file_path)

if __name__ == "__main__":
    logger.info("Starting Instagram Downloader Bot...")
    app.run()
