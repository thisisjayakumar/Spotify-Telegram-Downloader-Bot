# 🎵 Spotify Music Downloader Bot

A powerful Telegram bot that downloads music from Spotify tracks and playlists, then automatically uploads them to a Telegram channel/group.

## ✨ Features

- **Single Track Download** - Download individual Spotify tracks
- **Playlist Support** - Fetch and display all tracks in a playlist
- **Selective Download** - Choose specific tracks from a playlist
- **Batch Download** - Download all tracks with rate limiting
- **Auto-Upload** - Automatically upload to specified Telegram channel
- **File Cleanup** - Delete local files after successful upload
- **Progress Tracking** - Real-time download status updates
- **Cancel Operation** - Ability to cancel ongoing downloads

## 🛠️ Technologies Used

- Python 3.8+
- Pyrogram (MTProto API)
- aiohttp for async HTTP requests
- python-dotenv for configuration
- spotdown.org API for Spotify downloads

## 📋 Prerequisites

- Telegram Bot Token (from [@BotFather](https://t.me/botfather))
- Telegram API ID and Hash (from [my.telegram.org](https://my.telegram.org))
- Target Telegram group/channel where bot is admin
- Python 3.8 or higher

## 🚀 Installation

### 1. Clone the Repository
```bash
git clone https://github.com/yourusername/spotify-music-downloader-bot.git
cd spotify-music-downloader-bot

# 🎵 Spotify Music Downloader Bot

---

## 2. Create Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

## 3. Install Dependencies

```bash
pip install -r requirements.txt
```

## 4. Configure Environment Variables

Create a `.env` file in the root directory:

```env
API_ID=your_api_id
API_HASH=your_api_hash
BOT_TOKEN=your_bot_token
TARGET_CHAT_ID=your_channel_id  # Example: -1001234567890
```

---

## 🎮 Usage

**Start the bot:**

```bash
python bot.py
```

**Interact with the bot on Telegram:**

- Send `/start` to see welcome message
- Send any **Spotify track URL** to download a single song
- Send any **Spotify playlist URL** to see all tracks
- Select specific tracks or download all

---

## 📁 Project Structure

```text
spotify-music-downloader-bot/
├── bot.py              # Main bot script
├── requirements.txt    # Python dependencies
├── .env               # Environment variables
├── downloads/         # Temporary download folder
└── README.md          # This file
```

---

## ⚙️ Configuration Options

Edit these variables in `bot.py`:

```python
# Download settings
DOWNLOAD_PATH = "downloads"
MAX_CONCURRENT_DOWNLOADS = 3
DOWNLOAD_DELAY = 3  # seconds between downloads
MAX_FILE_SIZE = 2000 * 1024 * 1024  # 2000 MB
```

---

## 🐳 Docker Deployment

### Using Docker Compose (Recommended)

**Create `docker-compose.yml`:**

```yaml
version: '3.8'

services:
  spotify-bot:
    build: .
    container_name: spotify-downloader
    restart: unless-stopped
    volumes:
      - ./downloads:/app/downloads
      - ./.env:/app/.env
    environment:
      - TZ=Asia/Kolkata
```

**Create `Dockerfile`:**

```dockerfile
FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY bot.py .
COPY .env .

RUN mkdir -p downloads

CMD ["python", "bot.py"]
```

**Build and run:**

```bash
docker-compose up -d
```

---

## ☁️ Cloud Deployment (Systemd)

Create a service file `/etc/systemd/system/spotify-bot.service`:

```ini
[Unit]
Description=Spotify Downloader Telegram Bot
After=network.target

[Service]
Type=simple
User=your-user
WorkingDirectory=/path/to/bot/directory
Environment="PATH=/path/to/bot/directory/venv/bin"
ExecStart=/path/to/bot/directory/venv/bin/python /path/to/bot/directory/bot.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**Enable and start:**

```bash
sudo systemctl daemon-reload
sudo systemctl enable spotify-bot
sudo systemctl start spotify-bot
```

---

## 📊 Logging

Logs are displayed in the console with timestamps:

```text
2026-03-04 17:25:24,870 - __main__ - INFO - 🤖 Bot is now running!
2026-03-04 17:25:25,123 - __main__ - INFO - 📨 Received message from User
```

---

## 🔧 Troubleshooting

### Common Issues and Solutions

| Issue | Solution |
|-------|----------|
| **Bot not receiving messages** | Clear webhook: `curl -F "url=" https://api.telegram.org/bot<TOKEN>/setWebhook` |
| **Peer ID invalid** | Add peer fix patch in code (already included) |
| **Upload fails** | Ensure bot is admin in target channel |
| **Download fails** | Check spotdown.org API availability |

### Verify Bot Token

```bash
curl https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getMe
```

---

## 📝 Requirements File

Create `requirements.txt`:

```txt
pyrogram==2.0.106
aiohttp==3.9.1
python-dotenv==1.0.0
aiofiles==23.2.1
requests==2.31.0
tgcrypto==1.2.5  # Optional for speed
```

---

## 🚦 API Endpoints Used

- **`https://spotdown.org/api/song-details?url={url}`** — Get song/playlist details
- **`https://spotdown.org/api/check-direct-download?url={url}`** — Check download availability
- **`https://spotdown.org/api/download`** — Trigger download

---

## ⚠️ Important Notes

> **Storage:** Ensure sufficient disk space for temporary files
>
> **Rate Limits:** API may have rate limits; delays are built-in
>
> **File Size:** Telegram has a **2GB limit** for bot uploads
>
> **Bot Permissions:** Bot must be **admin** in target channel with post permissions
>
> **Privacy:** Disable group privacy mode in `@BotFather`

---

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit changes (`git commit -m 'Add AmazingFeature'`)
4. Push to branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

## 📄 License

This project is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- **[Pyrogram](https://pyrogram.org/)** for Telegram MTProto API
- **[spotdown.org](https://spotdown.org/)** for Spotify download API
- All contributors and users

---

## 📞 Contact

- **GitHub:** [@yourusername](https://github.com/yourusername)
- **Telegram:** [@yourtelegram](https://t.me/yourtelegram)

---

> ⭐ **Star this repo if you find it useful!**
