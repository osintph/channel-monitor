import asyncio
import json
import os
import argparse
import shutil
from pathlib import Path
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv
from telethon import TelegramClient
from telethon.tl.types import (
    MessageMediaPhoto, MessageMediaDocument, MessageMediaWebPage
)
from deep_translator import GoogleTranslator

# ─── CONFIG ────────────────────────────────────────────────────────────────────
load_dotenv()

API_ID       = int(os.getenv("TELEGRAM_API_ID"))
API_HASH     = os.getenv("TELEGRAM_API_HASH")
PHONE        = os.getenv("TELEGRAM_PHONE")
SESSION_NAME = "farsi_monitor"
LIMIT        = 200
# ───────────────────────────────────────────────────────────────────────────────

translator = GoogleTranslator(source="fa", target="en")


# ─── DISK SPACE ────────────────────────────────────────────────────────────────
def check_disk_space(min_gb: float, path: str = "/") -> None:
    """Check disk space at startup and abort if below threshold."""
    total, used, free = shutil.disk_usage(path)
    free_gb  = free  / (1024 ** 3)
    total_gb = total / (1024 ** 3)
    used_pct = (used / total) * 100
    print(f"[i] Disk space — Free: {free_gb:.2f} GB / Total: {total_gb:.2f} GB ({used_pct:.1f}% used)")
    if free_gb < min_gb:
        print(f"\n[✗] ABORT: Less than {min_gb} GB free ({free_gb:.2f} GB remaining).")
        print(f"[✗] Free up space before running again.")
        exit(1)


def assert_disk_space(min_gb: float, path: str = "/") -> bool:
    """Returns False if disk space is critically low — called before each download."""
    free = shutil.disk_usage(path).free / (1024 ** 3)
    if free < min_gb:
        print(f"\n[✗] CRITICAL: Disk space dropped below {min_gb} GB ({free:.2f} GB free). Stopping downloads.")
        return False
    return True


# ─── CLI ARGS ──────────────────────────────────────────────────────────────────
def parse_args():
    parser = argparse.ArgumentParser(
        description="Farsi Telegram Channel Monitor — downloads and translates messages to English",
        formatter_class=argparse.RawTextHelpFormatter
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "-c", "--channel",
        help="Single channel username or invite link\nExample: --channel irna_1931"
    )
    group.add_argument(
        "-f", "--file",
        help="Path to a text file with one channel per line\nExample: --file channels.txt"
    )
    parser.add_argument(
        "-l", "--limit",
        type=int,
        default=LIMIT,
        help=f"Number of messages to fetch per channel (default: {LIMIT}, use 0 for all)"
    )
    parser.add_argument(
        "-d", "--days",
        type=int,
        default=None,
        help="Only fetch messages from the last N days\nExample: --days 7"
    )
    parser.add_argument(
        "-o", "--output",
        default="output",
        help="Output directory (default: output/)"
    )
    parser.add_argument(
        "--max-video-mb",
        type=int,
        default=50,
        help="Max video size in MB to download (default: 50, use 0 to skip all videos)"
    )
    parser.add_argument(
        "--min-space-gb",
        type=float,
        default=1.0,
        help="Minimum free disk space in GB before aborting (default: 1.0)"
    )
    return parser.parse_args()


# ─── CHANNEL LOADER ────────────────────────────────────────────────────────────
def load_channels(args) -> list:
    if args.channel:
        return [args.channel.strip()]
    elif args.file:
        path = Path(args.file)
        if not path.exists():
            print(f"[!] File not found: {args.file}")
            exit(1)
        channels = []
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    channels.append(line)
        if not channels:
            print("[!] No channels found in file.")
            exit(1)
        print(f"[+] Loaded {len(channels)} channel(s) from {args.file}")
        return channels
    return []


# ─── TRANSLATION ───────────────────────────────────────────────────────────────
def translate_text(text: str) -> str:
    if not text or not text.strip():
        return ""
    try:
        chunk_size = 4500
        if len(text) <= chunk_size:
            return translator.translate(text)
        chunks = [text[i:i+chunk_size] for i in range(0, len(text), chunk_size)]
        return " ".join([translator.translate(c) for c in chunks])
    except Exception as e:
        return f"[Translation error: {e}]"


# ─── ENTITY FORMATTER ──────────────────────────────────────────────────────────
def format_entities(text: str, entities) -> str:
    import html
    if not text:
        return ""
    if not entities:
        return html.escape(text).replace("\n", "<br>")

    from telethon.tl.types import (
        MessageEntityBold, MessageEntityItalic, MessageEntityCode,
        MessageEntityPre, MessageEntityUrl, MessageEntityTextUrl,
        MessageEntityMention, MessageEntityHashtag
    )

    tags = []
    for ent in entities:
        s, l = ent.offset, ent.length
        seg_esc = html.escape(text[s:s+l])
        if isinstance(ent, MessageEntityBold):
            tags.append((s, s+l, "<b>", "</b>"))
        elif isinstance(ent, MessageEntityItalic):
            tags.append((s, s+l, "<i>", "</i>"))
        elif isinstance(ent, MessageEntityCode):
            tags.append((s, s+l, "<code>", "</code>"))
        elif isinstance(ent, MessageEntityPre):
            tags.append((s, s+l, "<pre>", "</pre>"))
        elif isinstance(ent, MessageEntityTextUrl):
            tags.append((s, s+l, f'<a href="{ent.url}" target="_blank">', "</a>"))
        elif isinstance(ent, MessageEntityUrl):
            tags.append((s, s+l, f'<a href="{seg_esc}" target="_blank">', "</a>"))
        elif isinstance(ent, MessageEntityMention):
            tags.append((s, s+l, '<span class="mention">', "</span>"))
        elif isinstance(ent, MessageEntityHashtag):
            tags.append((s, s+l, '<span class="hashtag">', "</span>"))

    output = html.escape(text)
    for s, e, open_t, close_t in sorted(tags, key=lambda x: x[0], reverse=True):
        seg = html.escape(text[s:e])
        output = output[:s] + open_t + seg + close_t + output[e:]

    return output.replace("\n", "<br>")


# ─── HTML GENERATOR ────────────────────────────────────────────────────────────
def generate_html(messages, channel_title, output_path):
    html_messages = []
    for m in reversed(messages):
        media_block = ""
        if m["media_type"] == "photo" and m["media_path"]:
            media_block = f'<img src="{m["media_path"]}" class="msg-photo" alt="photo">'
        elif m["media_type"] == "image_doc" and m["media_path"]:
            media_block = f'<img src="{m["media_path"]}" class="msg-photo" alt="image">'
        elif m["media_type"] == "video" and m["media_path"]:
            media_block = f'''
            <video controls class="msg-video">
                <source src="{m["media_path"]}">
                Your browser does not support video playback.
            </video>'''
        elif m["media_type"] == "video" and not m["media_path"]:
            media_block = '<div class="media-placeholder">🎥 Video (skipped — size limit or download error)</div>'
        elif m["media_type"] == "webpage" and m.get("media_url"):
            media_block = f'<div class="webpage-preview"><a href="{m["media_url"]}" target="_blank">🔗 {m["media_url"]}</a></div>'

        text_block = ""
        if m["formatted_html"]:
            text_block = f'''
            <div class="msg-text original" dir="rtl">{m["formatted_html"]}</div>
            <div class="msg-divider">🔽 English Translation</div>
            <div class="msg-text translated">{m["translated_en"]}</div>
            '''
        elif not m["formatted_html"] and m["media_type"]:
            text_block = '<div class="msg-text translated" style="color:#555">[No caption]</div>'

        meta_views = f'👁 {m["views"]}' if m["views"] else ""
        reply_badge = f'<span class="reply-badge">↩ Reply to #{m["reply_to"]}</span>' if m["reply_to"] else ""

        html_messages.append(f'''
        <div class="message" id="msg-{m["id"]}">
            <div class="msg-meta">
                <span class="msg-id">#{m["id"]}</span>
                <span class="msg-date">{m["date"]}</span>
                {reply_badge}
                <span class="msg-views">{meta_views}</span>
            </div>
            {media_block}
            {text_block}
        </div>
        ''')

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{channel_title} — Farsi → English</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: #0e0e0e; color: #e0e0e0;
            max-width: 780px; margin: 0 auto; padding: 20px;
        }}
        h1 {{ color: #29b6f6; border-bottom: 1px solid #333; padding-bottom: 10px; }}
        .stats {{ color: #555; font-size: 0.85em; margin-bottom: 24px; }}
        .message {{
            background: #1a1a2e; border-radius: 10px;
            padding: 14px 18px; margin-bottom: 16px;
            border-left: 3px solid #29b6f6;
        }}
        .msg-meta {{
            font-size: 0.75em; color: #888; margin-bottom: 8px;
            display: flex; gap: 12px; flex-wrap: wrap; align-items: center;
        }}
        .msg-id {{ color: #29b6f6; font-weight: bold; }}
        .reply-badge {{ background: #1e3a5f; padding: 2px 6px; border-radius: 4px; color: #90caf9; }}
        .msg-photo {{ max-width: 100%; border-radius: 8px; margin: 8px 0; display: block; }}
        .msg-video {{ max-width: 100%; border-radius: 8px; margin: 8px 0; display: block; background: #000; }}
        .msg-text {{ padding: 6px 0; line-height: 1.8; font-size: 0.97em; }}
        .original {{ color: #ffcc80; font-size: 1.05em; border-right: 3px solid #ff8f00; padding-right: 10px; }}
        .msg-divider {{ color: #444; font-size: 0.75em; margin: 6px 0; }}
        .translated {{ color: #a5d6a7; }}
        .media-placeholder {{ color: #777; font-style: italic; padding: 8px 0; }}
        .webpage-preview {{ background: #111; padding: 8px 12px; border-radius: 6px; margin: 6px 0; border: 1px solid #2a2a2a; }}
        .webpage-preview a {{ color: #29b6f6; text-decoration: none; }}
        .mention {{ color: #80cbc4; }}
        .hashtag {{ color: #ce93d8; }}
        code {{ background: #2a2a2a; padding: 2px 6px; border-radius: 3px; font-family: monospace; color: #ef9a9a; }}
        pre {{ background: #2a2a2a; padding: 12px; border-radius: 6px; overflow-x: auto; }}
        b {{ color: #ffffff; }}
        a {{ color: #29b6f6; }}
    </style>
</head>
<body>
    <h1>📡 {channel_title}</h1>
    <p class="stats">Farsi → English &nbsp;|&nbsp; {len(messages)} messages</p>
    {"".join(html_messages)}
</body>
</html>"""

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_content)


# ─── CHANNEL PROCESSOR ─────────────────────────────────────────────────────────
async def process_channel(client, channel_id, limit, output_dir,
                           days=None, min_space_gb=1.0, max_video_mb=50):
    try:
        channel = await client.get_entity(channel_id)
    except Exception as e:
        print(f"[!] Could not access channel '{channel_id}': {e}")
        return

    channel_title = getattr(channel, "title", str(channel_id))
    safe_name     = "".join(c if c.isalnum() else "_" for c in channel_title)

    channel_dir = output_dir / safe_name
    media_dir   = channel_dir / "media"
    channel_dir.mkdir(parents=True, exist_ok=True)
    media_dir.mkdir(exist_ok=True)

    cutoff_date = None
    if days:
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
        print(f"[i] Fetching messages since: {cutoff_date.strftime('%Y-%m-%d %H:%M UTC')} ({days} days back)")

    print(f"\n[+] Processing: {channel_title} ({channel_id})")

    results = []
    fetch_limit = None if limit == 0 else limit

    async for message in client.iter_messages(channel, limit=fetch_limit):

        # Date cutoff
        if cutoff_date and message.date < cutoff_date:
            print(f"  [i] Reached messages older than {days} days. Stopping.")
            break

        # Disk space check per message
        if not assert_disk_space(min_space_gb, str(output_dir)):
            print(f"  [i] Partial results saved up to message #{message.id}")
            break

        entry = {
            "id":             message.id,
            "date":           message.date.strftime("%Y-%m-%d %H:%M:%S UTC"),
            "original_fa":    message.text or "",
            "translated_en":  "",
            "formatted_html": "",
            "media_type":     None,
            "media_path":     None,
            "media_url":      None,
            "views":          getattr(message, "views", None),
            "forwards":       getattr(message, "forwards", None),
            "reply_to":       message.reply_to_msg_id if message.reply_to else None,
        }

        if message.text:
            entry["translated_en"]  = translate_text(message.text)
            entry["formatted_html"] = format_entities(message.text, message.entities)

        if message.media:
            if isinstance(message.media, MessageMediaPhoto):
                entry["media_type"] = "photo"
                if assert_disk_space(min_space_gb, str(output_dir)):
                    try:
                        filename = media_dir / f"{message.id}.jpg"
                        await client.download_media(message, file=str(filename))
                        entry["media_path"] = f"media/{message.id}.jpg"
                        print(f"  [+] Photo: {filename.name}")
                    except Exception as e:
                        print(f"  [!] Photo error: {e}")

            elif isinstance(message.media, MessageMediaDocument):
                doc  = message.media.document
                mime = getattr(doc, "mime_type", "")

                if mime.startswith("image/"):
                    entry["media_type"] = "image_doc"
                    ext = mime.split("/")[-1]
                    if assert_disk_space(min_space_gb, str(output_dir)):
                        try:
                            filename = media_dir / f"{message.id}.{ext}"
                            await client.download_media(message, file=str(filename))
                            entry["media_path"] = f"media/{message.id}.{ext}"
                            print(f"  [+] Image: {filename.name}")
                        except Exception as e:
                            print(f"  [!] Image error: {e}")

                elif mime.startswith("video/"):
                    entry["media_type"] = "video"
                    ext = mime.split("/")[-1]
                    ext = "mp4" if ext in ("mp4", "mpeg4") else ext
                    file_size_mb = getattr(doc, "size", 0) / (1024 * 1024)

                    if max_video_mb == 0:
                        print(f"  [i] Video skipped (--max-video-mb 0)")
                    elif file_size_mb > max_video_mb:
                        print(f"  [!] Video skipped — {file_size_mb:.1f} MB exceeds limit of {max_video_mb} MB")
                    elif assert_disk_space(min_space_gb, str(output_dir)):
                        try:
                            filename = media_dir / f"{message.id}.{ext}"
                            print(f"  [~] Downloading video ({file_size_mb:.1f} MB): {filename.name} ...")
                            await client.download_media(message, file=str(filename))
                            entry["media_path"] = f"media/{message.id}.{ext}"
                            print(f"  [+] Video saved: {filename.name}")
                        except Exception as e:
                            print(f"  [!] Video error: {e}")
                else:
                    entry["media_type"] = f"document ({mime})"

            elif isinstance(message.media, MessageMediaWebPage):
                wp = message.media.webpage
                entry["media_type"] = "webpage"
                entry["media_url"]  = getattr(wp, "url", None)

        results.append(entry)
        print(f"  [MSG {message.id}] {entry['date']} | {entry['media_type'] or 'text'}")

    # Save outputs
    json_path = channel_dir / "messages.json"
    html_path = channel_dir / "messages.html"

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    generate_html(results, channel_title, html_path)

    print(f"  [✓] {len(results)} messages saved → {channel_dir}/")
    print(f"  [✓] Open: firefox {html_path}")


# ─── MAIN ──────────────────────────────────────────────────────────────────────
async def main():
    args       = parse_args()
    channels   = load_channels(args)
    output_dir = Path(args.output)
    output_dir.mkdir(exist_ok=True)

    check_disk_space(min_gb=args.min_space_gb, path=str(output_dir))

    client = TelegramClient(SESSION_NAME, API_ID, API_HASH)
    await client.start(phone=PHONE)
    print(f"[+] Connected as {(await client.get_me()).username}")

    for channel_id in channels:
        await process_channel(
            client,
            channel_id,
            limit        = args.limit,
            output_dir   = output_dir,
            days         = args.days,
            min_space_gb = args.min_space_gb,
            max_video_mb = args.max_video_mb,
        )

    await client.disconnect()
    print(f"\n[+] All done. Output in: {output_dir}/")


if __name__ == "__main__":
    asyncio.run(main())

