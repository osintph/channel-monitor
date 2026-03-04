# 📡 Telegram Channel Monitor

A multi-language OSINT tool that downloads messages, photos, and videos from Telegram channels and automatically translates them into **English**, generating a styled HTML report and structured JSON output per channel.

Supports **Farsi, Russian, Chinese, Korean, Arabic, Ukrainian** and any other language via automatic detection. Built for monitoring foreign-language Telegram channels for intelligence and research purposes.

---

## Features

- Auto-detects message language per message using `langdetect`
- Translates any language → English via Google Translate
- Force a specific language per channel via `channels.txt` or `--lang` flag
- Downloads messages, photos, and videos from any Telegram channel
- Preserves message formatting (bold, italic, links, mentions, hashtags)
- RTL language support (Farsi, Arabic, etc.) rendered correctly in HTML
- Language flag badge per message in HTML output (🇮🇷 🇷🇺 🇨🇳 🇰🇵)
- Language breakdown summary per channel after each run
- Dark-themed HTML report with embedded media
- Structured JSON output for further processing or platform integration
- Multi-channel support via `channels.txt` with per-channel language tags
- Filter messages by number of days back (`--days`)
- Disk space guard — aborts if storage runs low
- Video size limit to prevent runaway downloads
- Skip English messages (`--skip-english`) to avoid unnecessary translation
- Secure credential management via `.env` file

---

## Requirements

- Python 3.11+
- Telegram account with API credentials from [my.telegram.org](https://my.telegram.org)

---

## Installation

```bash
# Clone the repo
git clone https://github.com/osintph/channel-monitor.git
cd channel-monitor

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Set up credentials
cp .env.example .env
nano .env
```

---

## Getting Your Telegram API Credentials

1. Go to [https://my.telegram.org](https://my.telegram.org)
2. Log in with your phone number
3. Click **API Development Tools**
4. Create an application — set Platform to **Other**
5. Copy your `api_id` and `api_hash` into `.env`

---

## Configuration

`.env` file:

```bash
TELEGRAM_API_ID=your_api_id
TELEGRAM_API_HASH=your_api_hash
TELEGRAM_PHONE=+your_phone_number
```

---

## Usage

```bash
source venv/bin/activate

# Single channel — auto-detect language
python channel_monitor.py --channel irna_1931

# Single channel — force language
python channel_monitor.py --channel rt_russian --lang ru

# Last 7 days only
python channel_monitor.py --channel irna_1931 --days 7

# Multiple channels from file (with per-channel language tags)
python channel_monitor.py --file channels.txt

# Last 30 days, skip videos over 25MB, abort if under 2GB free
python channel_monitor.py --file channels.txt --days 30 --max-video-mb 25 --min-space-gb 2

# All messages, no videos, skip English messages
python channel_monitor.py --channel some_channel --limit 0 --max-video-mb 0 --skip-english

# Custom output directory
python channel_monitor.py --file channels.txt --output ~/reports
```

---

## CLI Options

| Flag | Default | Description |
|------|---------|-------------|
| `-c`, `--channel` | — | Single channel username or invite link |
| `-f`, `--file` | — | Text file with one channel per line |
| `-l`, `--limit` | 200 | Messages to fetch per channel (0 = all) |
| `-d`, `--days` | None | Only fetch messages from last N days |
| `--lang` | auto | Force source language code (e.g. `ru`, `fa`, `zh-cn`, `ko`) |
| `--skip-english` | off | Skip translation for messages detected as English |
| `-o`, `--output` | output/ | Output directory |
| `--max-video-mb` | 50 | Max video size in MB (0 = skip all videos) |
| `--min-space-gb` | 1.0 | Abort if free disk space drops below this |

---

## Supported Languages

| Language | Code | Flag |
|----------|------|------|
| Farsi/Persian | `fa` | 🇮🇷 |
| Russian | `ru` | 🇷🇺 |
| Chinese (Simplified) | `zh-cn` | 🇨🇳 |
| Chinese (Traditional) | `zh-tw` | 🇹🇼 |
| Korean | `ko` | 🇰🇵 |
| Arabic | `ar` | 🇸🇦 |
| Ukrainian | `uk` | 🇺🇦 |
| German | `de` | 🇩🇪 |
| French | `fr` | 🇫🇷 |
| Spanish | `es` | 🇪🇸 |
| Auto-detect | `auto` | 🌐 |

---

## `channels.txt` Format

```txt
# format: channel_username::language_code
# language tag is optional — omit for auto-detect

irna_1931::fa
rt_russian::ru
xinhua_news::zh-cn
rodong_official::ko

# No language tag = auto-detect
some_unknown_channel
```

Lines starting with `#` are ignored.

---

## Output Structure

```
output/
├── Channel_Name/
│   ├── messages.html    ← Open in browser
│   ├── messages.json    ← Structured data
│   └── media/
│       ├── 10001.jpg
│       ├── 10002.mp4
│       └── ...
└── Another_Channel/
    └── ...
```

```bash
firefox output/Channel_Name/messages.html
```

---

## OPSEC Warning

- Never commit `.env` or `.session` files to Git
- API credentials are permanently tied to your Telegram account
- Consider using a dedicated number for sensitive OSINT work
- Only monitor channels you are authorized to access

---

## License

MIT License — free to use, modify, and distribute for research purposes.

---

*Built by [Sigmund](https://cybernewsph.com) for OSINT monitoring of foreign-language Telegram channels.*

