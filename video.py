import requests
import aria2p
from datetime import datetime
import asyncio
import os
import time
import logging
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# ---- Aria2 Setup ----
aria2 = aria2p.API(
    aria2p.Client(
        host="http://localhost",
        port=6800,
        secret=""
    )
)

aria2.set_global_options({
    "max-tries": "50",
    "retry-wait": "2",
    "continue": "true",
    "split": "16",
    "min-split-size": "1M",
    "max-connection-per-server": "16",
    "user-agent": "Mozilla/5.0"
})

# ---- Format Progress ----
def format_progress_bar(filename, percentage, done, total_size, status, eta, speed, elapsed, user_mention, user_id, aria2p_gid):
    percent_str = f"{percentage:.2f}%"
    done_mb = f"{int(done) / (1024 * 1024):.2f} MB"
    total_mb = f"{int(total_size) / (1024 * 1024):.2f} MB"
    speed_kb = f"{int(speed) / 1024:.2f} KB/s"
    bar = "★" * int(percentage / 10) + "☆" * (10 - int(percentage / 10))
    return (
        f"┌─── FILEᴺᴬᴹᴱ:\n├ `{filename}`\n"
        f"├─ [{bar}] {percent_str}\n"
        f"├─ ᴘʀᴏᴄᴇssᴇᴅ: {done_mb} OF {total_mb}\n"
        f"├─ sᴛᴀᴛᴜs: {status}\n"
        f"├─ sᴘᴇᴇᴅ: {speed_kb}\n"
        f"└─ ᴜsᴇʀ: 🤝 | ID: `{user_id}`"
    )

# ---- Download Video ----
async def download_video(url, reply_msg, user_mention, user_id):
    try:
        response = requests.get(f"https://terabox.pikaapis.workers.dev/?url={url}")
        response.raise_for_status()
        data = response.json()

        video_title = data["file_name"]
        download_link = data.get("direct_link") or data["link"]
        thumbnail_url = data["thumb"]

        download = aria2.add_uris([download_link])
        start_time = datetime.now()

        while not download.is_complete:
            download.update()
            percentage = download.progress
            done = download.completed_length
            total_size = download.total_length
            speed = download.download_speed
            eta = download.eta
            elapsed = (datetime.now() - start_time).total_seconds()

            progress_text = format_progress_bar(
                filename=video_title,
                percentage=percentage,
                done=done,
                total_size=total_size,
                status="Downloading",
                eta=eta,
                speed=speed,
                elapsed=elapsed,
                user_mention=user_mention,
                user_id=user_id,
                aria2p_gid=download.gid
            )
            await reply_msg.edit_text(progress_text)
            await asyncio.sleep(2)

        if download.is_complete:
            file_path = download.files[0].path

            thumbnail_path = f"thumb_{user_id}.jpg"
            thumbnail_data = requests.get(thumbnail_url)
            with open(thumbnail_path, "wb") as f:
                f.write(thumbnail_data.content)

            await reply_msg.edit_text("ᴜᴘʟᴏᴀᴅɪɴɢ...")
            return file_path, thumbnail_path, video_title

    except Exception as e:
        logging.error(f"Download error: {e}")
        await reply_msg.reply_text("❌ Could not download the video. Try again later.")
        return None, None, None

# ---- Upload Video ----
async def upload_video(client, file_path, thumbnail_path, video_title, reply_msg, collection_channel_id, user_mention, user_id, message):
    file_size = os.path.getsize(file_path)
    uploaded = 0
    start_time = datetime.now()
    last_update_time = time.time()

    async def progress(current, total):
        nonlocal uploaded, last_update_time
        uploaded = current
       
