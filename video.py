import requests
import aria2p
from datetime import datetime
from status import format_progress_bar
import asyncio
import os
import logging

# Setup aria2 client
aria2 = aria2p.API(
    aria2p.Client(
        host="http://localhost",
        port=6800,
        secret=""
    )
)

# Speed optimized global settings for aria2
aria2.set_global_options({
    "max-tries": "50",
    "retry-wait": "2",
    "continue": "true",
    "split": "16",
    "min-split-size": "1M",
    "max-connection-per-server": "16",
    "user-agent": "Mozilla/5.0"
})

# Updated function using direct_link (preferred), aria2p, and formatted progress bar
async def download_video(url, reply_msg, user_mention, user_id):
    try:
        # Call API
        response = requests.get(f"https://terabox.pikaapis.workers.dev/?url={url}")
        response.raise_for_status()
        data = response.json()

        # Extract info
        video_title = data["file_name"]
        download_link = data.get("direct_link") or data["link"]
        thumbnail_url = data["thumb"]

        # Start aria2 download
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

            # Save thumbnail
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
