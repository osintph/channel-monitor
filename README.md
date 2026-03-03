# 📡 Farsi Telegram Channel Monitor

An OSINT tool that downloads messages, photos, and videos from Telegram channels and automatically translates them from **Farsi (Persian) → English**, generating a styled HTML report and structured JSON output.

Built for monitoring Farsi-language Telegram channels during the Iran conflict for intelligence and research purposes.

---

## Features

- Downloads messages, photos, and videos from any Telegram channel
- Translates Farsi text to English via Google Translate
- Preserves message formatting (bold, italic, links, mentions, hashtags)
- Generates a dark-themed HTML report with embedded media
- Saves structured JSON output for further processing
- Multi-channel support via a channels list file
- Filter messages by number of days back
- Disk space guard — aborts if storage runs low
- Video size limit to prevent runaway downloads
- Secure credential management via `.env` file

---

## Requirements

- Python 3.11+
- Telegram account with API credentials from [my.telegram.org](https://my.telegram.org)

---

## Installation

```bash
# Clone the repo
git clone https://github.com/osintph/farsimonitor.git
cd farsimonitor

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

# Single channel
python farsi_monitor.py --channel irna_1931

# Single channel, last 7 days only
python farsi_monitor.py --channel irna_1931 --days 7

# Multiple channels from file
python farsi_monitor.py --file channels.txt

# Last 30 days, skip videos over 25MB, abort if under 2GB free
python farsi_monitor.py --file channels.txt --days 30 --max-video-mb 25 --min-space-gb 2

# Fetch all messages, no videos, custom output dir
python farsi_monitor.py --channel irna_1931 --limit 0 --max-video-mb 0 --output ~/reports
```

---

## CLI Options

| Flag | Default | Description |
|------|---------|-------------|
| `-c`, `--channel` | — | Single channel username or invite link |
| `-f`, `--file` | — | Text file with one channel per line |
| `-l`, `--limit` | 200 | Messages to fetch per channel (0 = all) |
| `-d`, `--days` | None | Only fetch messages from last N days |
| `-o`, `--output` | output/ | Output directory |
| `--max-video-mb` | 50 | Max video size in MB (0 = skip all videos) |
| `--min-space-gb` | 1.0 | Abort if free disk space drops below this |

---

## channels.txt Format

```txt
# Iranian state media
irna_1931
tasnimnews
mehrnews_agency

# Add invite links directly
https://t.me/example_invite
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

*Built by [Sigmund](https://cybernewsph.com) for OSINT monitoring of Farsi Telegram channels.*

