import os
import asyncio
import aiohttp
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional
import pyrogram
from pyrogram import Client, filters, utils
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from pyrogram.enums import ParseMode
from pyrogram.errors import FloodWait
import logging
from pathlib import Path
from dotenv import load_dotenv

def get_peer_type_new(peer_id: int) -> str:
    """Fixed peer type detection for Pyrogram"""
    peer_id_str = str(peer_id)
    if not peer_id_str.startswith("-"):
        return "user"
    elif peer_id_str.startswith("-100"):
        return "channel"  # Supergroups and channels
    else:
        return "chat"     # Basic groups

# Apply the patch
utils.get_peer_type = get_peer_type_new

# Get the directory where this script is located
script_dir = Path(__file__).parent.absolute()
env_path = script_dir / '.env'

# Load .env with explicit path
loaded = load_dotenv(dotenv_path=env_path)
print(f"DEBUG - .env file loaded: {loaded} from {env_path}")


# ================= CONFIG =================

print("DEBUG - Raw environment values:")
print(f"API_ID from env: {os.getenv('API_ID')}")
print(f"API_HASH from env: {os.getenv('API_HASH')}")
print(f"BOT_TOKEN from env: {os.getenv('BOT_TOKEN')}")
print(f"TARGET_CHAT_ID from env: {os.getenv('TARGET_CHAT_ID')}")

# Telegram Bot Configuration
API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
TARGET_CHAT_ID = int(os.getenv("TARGET_CHAT_ID", "-1003322931446"))

print(f"DEBUG - Parsed values:")
print(f"API_ID: {API_ID}")
print(f"API_HASH: {API_HASH}")
print(f"BOT_TOKEN: {BOT_TOKEN}")
print(f"TARGET_CHAT_ID: {TARGET_CHAT_ID}")

# Download settings
DOWNLOAD_PATH = "downloads"
MAX_CONCURRENT_DOWNLOADS = 3
DOWNLOAD_DELAY = 3  # seconds between downloads
MAX_FILE_SIZE = 2000 * 1024 * 1024  # 2000 MB (Telegram limit)

# API Endpoints
SPOTDOWN_API = "https://spotdown.org/api"
CHECK_DIRECT_URL = f"{SPOTDOWN_API}/check-direct-download"
DOWNLOAD_URL = f"{SPOTDOWN_API}/download"
SONG_DETAILS_URL = f"{SPOTDOWN_API}/song-details"

# ==========================================

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create download directory if it doesn't exist
Path(DOWNLOAD_PATH).mkdir(parents=True, exist_ok=True)


class SpotifyDownloader:
    def __init__(self):
        self.download_semaphore = asyncio.Semaphore(MAX_CONCURRENT_DOWNLOADS)
        self.active_downloads = {}
        self.user_sessions = {}

    async def fetch_song_details(self, url: str) -> Optional[Dict]:
        """Fetch song details from spotdown API"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{SONG_DETAILS_URL}?url={url}") as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        logger.error(f"Failed to fetch song details: {response.status}")
                        return None
        except Exception as e:
            logger.error(f"Error fetching song details: {e}")
            return None

    async def check_direct_download(self, url: str) -> bool:
        """Check if direct download is available"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{CHECK_DIRECT_URL}?url={url}") as response:
                    if response.status == 200:
                        data = await response.json()
                        return data.get("cached", False)
                    return False
        except Exception as e:
            logger.error(f"Error checking direct download: {e}")
            return False

    async def download_song(self, url: str, song_info: Dict, user_id: int) -> Optional[str]:
        """Download a single song"""
        async with self.download_semaphore:
            try:
                # Prepare filename
                filename = f"{song_info['artist']} - {song_info['title']}.mp3"
                filename = "".join(c for c in filename if c.isalnum() or c in " -._").strip()
                filepath = os.path.join(DOWNLOAD_PATH, f"{user_id}_{filename}")

                # Check if already downloading
                if url in self.active_downloads:
                    return self.active_downloads[url]

                self.active_downloads[url] = filepath

                # Trigger download
                async with aiohttp.ClientSession() as session:
                    payload = {"url": url}
                    async with session.post(DOWNLOAD_URL, json=payload) as response:
                        if response.status == 200:
                            # Get the actual download URL from response
                            # Note: You might need to adjust this based on actual API response
                            download_data = await response.json()
                            download_link = download_data.get("downloadUrl") or download_data.get("url")

                            if download_link:
                                # Download the file
                                async with session.get(download_link) as file_response:
                                    if file_response.status == 200:
                                        with open(filepath, 'wb') as f:
                                            async for chunk in file_response.content.iter_chunked(8192):
                                                f.write(chunk)
                                        
                                        logger.info(f"Downloaded: {filename}")
                                        await asyncio.sleep(DOWNLOAD_DELAY)
                                        return filepath
                        
                        # Alternative download method if direct link not available
                        # This might need adjustment based on actual API behavior
                        with open(filepath, 'wb') as f:
                            async for chunk in response.content.iter_chunked(8192):
                                f.write(chunk)
                        
                        logger.info(f"Downloaded: {filename}")
                        await asyncio.sleep(DOWNLOAD_DELAY)
                        return filepath

            except Exception as e:
                logger.error(f"Error downloading song: {e}")
                return None
            finally:
                if url in self.active_downloads:
                    del self.active_downloads[url]

    def clean_up_file(self, filepath: str):
        """Remove file after upload"""
        try:
            if os.path.exists(filepath):
                os.remove(filepath)
                logger.info(f"Deleted: {filepath}")
        except Exception as e:
            logger.error(f"Error deleting file: {e}")


# Initialize bot and downloader
app = Client(
    "spotify_downloader_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)
downloader = SpotifyDownloader()


# ================= Bot Handlers =================
# Add this temporary debug handler to see all messages

@app.on_message(filters.command(["start"]))
async def start_command(client: Client, message: Message):
    """Handle /start command"""
    welcome_text = (
        "🎵 **Spotify Music Downloader Bot**\n\n"
        "Send me a Spotify track or playlist URL and I'll download it for you!\n\n"
        "**Commands:**\n"
        "/start - Show this message\n"
        "/help - Show help\n"
        "/cancel - Cancel current operation\n\n"
        "**Examples:**\n"
        "• Track: https://open.spotify.com/track/...\n"
        "• Playlist: https://open.spotify.com/playlist/..."
    )
    await message.reply(welcome_text, parse_mode=ParseMode.MARKDOWN)


@app.on_message(filters.command(["help"]))
async def help_command(client: Client, message: Message):
    """Handle /help command"""
    help_text = (
        "**How to use:**\n\n"
        "1. Send a Spotify track URL to download a single song\n"
        "2. Send a Spotify playlist URL to see all tracks\n"
        "3. Choose which tracks to download\n"
        "4. Wait for downloads to complete\n"
        "5. Files will be automatically uploaded to the channel\n\n"
        "**Note:** Downloads may take some time depending on the number of tracks."
    )
    await message.reply(help_text, parse_mode=ParseMode.MARKDOWN)


@app.on_message(filters.command(["cancel"]))
async def cancel_command(client: Client, message: Message):
    """Handle /cancel command"""
    user_id = message.from_user.id
    if user_id in downloader.user_sessions:
        downloader.user_sessions[user_id]["cancelled"] = True
    await message.reply("✅ Current operation cancelled.")


@app.on_message(filters.regex(r"https?://(open\.spotify\.com|spotify\.link)/.+"))
async def handle_spotify_url(client: Client, message: Message):
    """Handle Spotify URLs"""
    url = message.text.strip()
    user_id = message.from_user.id
    
    # Initialize user session
    downloader.user_sessions[user_id] = {"cancelled": False}
    
    # Send initial status
    status_msg = await message.reply("🔍 Fetching information...")
    
    try:
        # Fetch song details
        song_data = await downloader.fetch_song_details(url)
        
        if not song_data or "songs" not in song_data:
            await status_msg.edit("❌ Failed to fetch song information. Please check the URL and try again.")
            return
        
        songs = song_data["songs"]
        
        # Handle single track
        if len(songs) == 1:
            await handle_single_track(client, message, songs[0], status_msg, user_id)
        
        # Handle playlist
        else:
            await handle_playlist(client, message, songs, status_msg, user_id)
            
    except Exception as e:
        logger.error(f"Error processing URL: {e}")
        await status_msg.edit(f"❌ An error occurred: {str(e)}")
    finally:
        if user_id in downloader.user_sessions:
            del downloader.user_sessions[user_id]

@app.on_message()
async def debug_all_messages(client: Client, message: Message):
    """Debug handler that passes messages through"""
    logger.info(f"📨 Received message from {message.from_user.first_name if message.from_user else 'Unknown'}")
    logger.info(f"📝 Message text: {message.text}")
    logger.info(f"🤖 Chat type: {message.chat.type}")
    logger.info(f"🆔 Chat ID: {message.chat.id}")
    
    # This is CRITICAL - let other handlers process the message
    await client.skip_updates()  # This tells Pyrogram to continue to next handlers
    # OR simply do nothing and let it continue naturally

async def handle_single_track(client: Client, message: Message, song: Dict, status_msg: Message, user_id: int):
    """Handle single track download"""
    # Show track info
    track_info = (
        f"**Track Found:**\n\n"
        f"🎵 **Title:** {song['title']}\n"
        f"👤 **Artist:** {song['artist']}\n"
        f"💿 **Album:** {song['album']}\n"
        f"⏱️ **Duration:** {song['duration']}\n"
    )
    
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Download", callback_data=f"download_single_{user_id}"),
            InlineKeyboardButton("❌ Cancel", callback_data=f"cancel_{user_id}")
        ]
    ])
    
    await status_msg.edit(track_info, reply_markup=keyboard, parse_mode=ParseMode.MARKDOWN)
    
    # Store song info for callback
    downloader.user_sessions[user_id]["current_song"] = song
    downloader.user_sessions[user_id]["is_playlist"] = False


async def handle_playlist(client: Client, message: Message, songs: List[Dict], status_msg: Message, user_id: int):
    """Handle playlist - show track list for selection"""
    playlist_info = f"**Playlist Found - {len(songs)} Tracks**\n\n"
    
    # Create track list (limited to first 20 for display)
    track_list = []
    for i, song in enumerate(songs[:20], 1):
        track_list.append(f"{i}. **{song['title']}** - {song['artist']}")
    
    playlist_info += "\n".join(track_list)
    
    if len(songs) > 20:
        playlist_info += f"\n\n... and {len(songs) - 20} more tracks"
    
    # Create selection keyboard
    keyboard_buttons = [
        [InlineKeyboardButton("📥 Download All", callback_data=f"download_all_{user_id}")]
    ]
    
    # Add individual track selection (limited to first 10 for UI)
    for i, song in enumerate(songs[:10], 1):
        keyboard_buttons.append([
            InlineKeyboardButton(f"{i}. {song['title'][:30]}", callback_data=f"download_{i}_{user_id}")
        ])
    
    if len(songs) > 10:
        keyboard_buttons.append([InlineKeyboardButton("📋 Show More...", callback_data=f"more_{user_id}_10")])
    
    keyboard_buttons.append([InlineKeyboardButton("❌ Cancel", callback_data=f"cancel_{user_id}")])
    
    keyboard = InlineKeyboardMarkup(keyboard_buttons)
    
    await status_msg.edit(playlist_info, reply_markup=keyboard, parse_mode=ParseMode.MARKDOWN)
    
    # Store playlist info
    downloader.user_sessions[user_id]["playlist"] = songs
    downloader.user_sessions[user_id]["is_playlist"] = True
    downloader.user_sessions[user_id]["page"] = 0


@app.on_callback_query()
async def handle_callback(client: Client, callback_query: CallbackQuery):
    """Handle callback queries from inline keyboards"""
    data = callback_query.data
    user_id = callback_query.from_user.id
    message = callback_query.message
    
    # Verify user
    if str(user_id) not in data and f"_{user_id}" not in data:
        await callback_query.answer("This action is not for you!", show_alert=True)
        return
    
    await callback_query.answer()
    
    # Handle different callback types
    if data.startswith("download_single"):
        await download_single_track(client, message, user_id)
    
    elif data.startswith("download_all"):
        await download_playlist_all(client, message, user_id)
    
    elif data.startswith("download_"):
        # Extract track index
        parts = data.split("_")
        if len(parts) >= 3 and parts[1].isdigit():
            track_index = int(parts[1]) - 1
            await download_specific_track(client, message, user_id, track_index)
    
    elif data.startswith("more_"):
        parts = data.split("_")
        if len(parts) >= 3 and parts[2].isdigit():
            start_index = int(parts[2])
            await show_more_tracks(client, message, user_id, start_index)
    
    elif data.startswith("cancel"):
        await cancel_operation(client, message, user_id)


async def download_single_track(client: Client, message: Message, user_id: int):
    """Download and upload a single track"""
    if user_id not in downloader.user_sessions or "current_song" not in downloader.user_sessions[user_id]:
        await message.edit("❌ Session expired. Please send the URL again.")
        return
    
    song = downloader.user_sessions[user_id]["current_song"]
    
    await message.edit(f"⏬ Downloading: **{song['title']}**...")
    
    # Download the song
    filepath = await downloader.download_song(song['url'], song, user_id)
    
    if filepath and os.path.exists(filepath):
        # Upload to Telegram
        await message.edit(f"📤 Uploading: **{song['title']}**...")
        
        try:
            # Send to target channel
            caption = f"🎵 **{song['title']}**\n👤 {song['artist']}\n⏱️ {song['duration']}"
            await client.send_audio(
                TARGET_CHAT_ID,
                filepath,
                caption=caption,
                title=song['title'],
                performer=song['artist'],
                duration=int(song['duration'].split(':')[0]) * 60 + int(song['duration'].split(':')[1])
            )
            
            # Send confirmation to user
            await message.edit(f"✅ Successfully downloaded and uploaded: **{song['title']}**")
            
            # Clean up
            downloader.clean_up_file(filepath)
            
        except Exception as e:
            await message.edit(f"❌ Error uploading: {str(e)}")
            logger.error(f"Upload error: {e}")
    else:
        await message.edit(f"❌ Failed to download: **{song['title']}**")


async def download_playlist_all(client: Client, message: Message, user_id: int):
    """Download all tracks in a playlist"""
    if user_id not in downloader.user_sessions or "playlist" not in downloader.user_sessions[user_id]:
        await message.edit("❌ Session expired. Please send the URL again.")
        return
    
    songs = downloader.user_sessions[user_id]["playlist"]
    
    await message.edit(f"⏬ Starting download of {len(songs)} tracks...")
    
    downloaded = 0
    failed = 0
    
    for i, song in enumerate(songs, 1):
        # Check if cancelled
        if downloader.user_sessions[user_id].get("cancelled", False):
            await message.edit(f"⚠️ Download cancelled. Downloaded: {downloaded}, Failed: {failed}")
            return
        
        # Update status
        await message.edit(f"⏬ Downloading {i}/{len(songs)}: **{song['title']}**...")
        
        # Download
        filepath = await downloader.download_song(song['url'], song, user_id)
        
        if filepath and os.path.exists(filepath):
            try:
                # Upload
                caption = f"🎵 **{song['title']}**\n👤 {song['artist']}\n⏱️ {song['duration']}"
                await client.send_audio(
                    TARGET_CHAT_ID,
                    filepath,
                    caption=caption,
                    title=song['title'],
                    performer=song['artist'],
                    duration=int(song['duration'].split(':')[0]) * 60 + int(song['duration'].split(':')[1])
                )
                
                downloaded += 1
                downloader.clean_up_file(filepath)
                
            except Exception as e:
                failed += 1
                logger.error(f"Upload error for {song['title']}: {e}")
        else:
            failed += 1
    
    # Final status
    await message.edit(f"✅ **Download Complete!**\n\n📥 Downloaded: {downloaded}\n❌ Failed: {failed}")


async def download_specific_track(client: Client, message: Message, user_id: int, track_index: int):
    """Download a specific track from playlist"""
    if user_id not in downloader.user_sessions or "playlist" not in downloader.user_sessions[user_id]:
        await message.edit("❌ Session expired. Please send the URL again.")
        return
    
    songs = downloader.user_sessions[user_id]["playlist"]
    
    if track_index < 0 or track_index >= len(songs):
        await message.edit("❌ Invalid track selection.")
        return
    
    song = songs[track_index]
    
    await message.edit(f"⏬ Downloading: **{song['title']}**...")
    
    # Download
    filepath = await downloader.download_song(song['url'], song, user_id)
    
    if filepath and os.path.exists(filepath):
        try:
            # Upload
            caption = f"🎵 **{song['title']}**\n👤 {song['artist']}\n⏱️ {song['duration']}"
            await client.send_audio(
                TARGET_CHAT_ID,
                filepath,
                caption=caption,
                title=song['title'],
                performer=song['artist'],
                duration=int(song['duration'].split(':')[0]) * 60 + int(song['duration'].split(':')[1])
            )
            
            await message.edit(f"✅ Successfully downloaded and uploaded: **{song['title']}**")
            downloader.clean_up_file(filepath)
            
        except Exception as e:
            await message.edit(f"❌ Error uploading: {str(e)}")
    else:
        await message.edit(f"❌ Failed to download: **{song['title']}**")


async def show_more_tracks(client: Client, message: Message, user_id: int, start_index: int):
    """Show more tracks in playlist"""
    if user_id not in downloader.user_sessions or "playlist" not in downloader.user_sessions[user_id]:
        await message.edit("❌ Session expired. Please send the URL again.")
        return
    
    songs = downloader.user_sessions[user_id]["playlist"]
    end_index = min(start_index + 10, len(songs))
    
    # Create track list
    track_list = []
    for i in range(start_index, end_index):
        song = songs[i]
        track_list.append(f"{i+1}. **{song['title']}** - {song['artist']}")
    
    playlist_info = f"**Tracks {start_index+1}-{end_index} of {len(songs)}**\n\n"
    playlist_info += "\n".join(track_list)
    
    # Create selection keyboard
    keyboard_buttons = []
    
    for i in range(start_index, end_index):
        keyboard_buttons.append([
            InlineKeyboardButton(f"{i+1}. {songs[i]['title'][:30]}", callback_data=f"download_{i+1}_{user_id}")
        ])
    
    # Navigation buttons
    nav_buttons = []
    if start_index > 0:
        nav_buttons.append(InlineKeyboardButton("⬅️ Previous", callback_data=f"more_{user_id}_{start_index-10}"))
    if end_index < len(songs):
        nav_buttons.append(InlineKeyboardButton("Next ➡️", callback_data=f"more_{user_id}_{end_index}"))
    
    if nav_buttons:
        keyboard_buttons.append(nav_buttons)
    
    keyboard_buttons.append([
        InlineKeyboardButton("📥 Download All", callback_data=f"download_all_{user_id}"),
        InlineKeyboardButton("❌ Cancel", callback_data=f"cancel_{user_id}")
    ])
    
    keyboard = InlineKeyboardMarkup(keyboard_buttons)
    
    await message.edit(playlist_info, reply_markup=keyboard, parse_mode=ParseMode.MARKDOWN)
    
    downloader.user_sessions[user_id]["page"] = start_index // 10


async def cancel_operation(client: Client, message: Message, user_id: int):
    """Cancel current operation"""
    if user_id in downloader.user_sessions:
        downloader.user_sessions[user_id]["cancelled"] = True
    
    await message.edit("✅ Operation cancelled.")

async def verify_target_chat():
        """Verify target chat exists and bot has access"""
        try:
            # Try to get chat info
            chat = await app.get_chat(TARGET_CHAT_ID)
            logger.info(f"✅ Target chat verified: {chat.title} (ID: {chat.id})")
            logger.info(f"📌 Chat type: {chat.type}")
            logger.info(f"📌 Bot is admin: {getattr(chat, 'is_admin', False)}")
            
            if not getattr(chat, 'is_admin', False):
                logger.warning("⚠️ Bot is not an admin in the target chat! Uploads may fail.")
                
            return True
        except Exception as e:
            logger.error(f"❌ Failed to access target chat: {e}")
            logger.error("\n🔧 Troubleshooting steps:")
            logger.error("1. Ensure bot is ADMIN in the target group/channel")
            logger.error("2. Send a message in the group mentioning @YourBotUsername")
            logger.error("3. Check @BotFather to disable Group Privacy mode")
            logger.error("4. Remove and re-add the bot to the group")
            return False
    
# ================= Main =================
async def main():
    """Main function to run the bot"""
    logger.info("Starting Spotify Downloader Bot...")
    
    # Start the client
    await app.start()
    logger.info("✅ Bot client started!")
    
    # ===== CRITICAL: Clear any existing webhook =====
    try:
        # Get current webhook info
        webhook_info = await app.get_webhook_info()
        logger.info(f"📡 Current webhook: {webhook_info.url}")
        
        if webhook_info.url:
            # Delete the webhook
            await app.delete_webhook(drop_pending_updates=True)  # Also drop pending updates
            logger.info("✅ Webhook cleared and pending updates dropped!")
        else:
            logger.info("✅ No webhook set, using polling mode")
    except Exception as e:
        logger.error(f"⚠️ Could not check/clear webhook: {e}")
    # =================================================
    
    # Get bot info
    me = await app.get_me()
    logger.info(f"🤖 Bot: @{me.username} (ID: {me.id})")
    
    # Test message to yourself (you said this works)
    try:
        YOUR_USER_ID = 1001721054  # Replace with your actual user ID
        await app.send_message(YOUR_USER_ID, "Bot is online and ready to receive messages! 🚀")
        logger.info(f"✅ Test message sent to user {YOUR_USER_ID}")
    except Exception as e:
        logger.error(f"❌ Could not send test message: {e}")
    
    # Verify target chat
    await verify_target_chat()
    
    logger.info("🤖 Bot is now running! Press Ctrl+C to stop.")
    
    # Use Pyrogram's idle
    await pyrogram.idle()


if __name__ == "__main__":
    try:
        # Optional: uvloop for performance
        try:
            import uvloop
            uvloop.install()
            logger.info("✅ uvloop installed for better performance")
        except ImportError:
            pass
        
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("👋 Bot stopped by user")
    except Exception as e:
        logger.error(f"💥 Fatal error: {e}")
        import traceback
        traceback.print_exc()