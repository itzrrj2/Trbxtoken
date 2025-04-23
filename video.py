import requests
import aria2p
import asyncio
import os
import time
import logging
from datetime import datetime
from status import format_progress_bar

# Initialize aria2 client
aria2 = aria2p.API(
    aria2p.Client(
        host="http://localhost",
        port=6800,
        secret=""
    )
)

# Set optimized global options for aria2
aria2.set_global_options({
    "max-tries": "50",
    "retry-wait": "2",
    "continue": "true",
    "split": "16",
    "min-split-size": "1M",
    "max-connection-per-server": "16",
    "user-agent": "Mozilla/5.0"
})


# --- Download Video Function ---
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
            thumb_data = requests.get(thumbnail_url)
            with open(thumbnail_path, "wb") as f:
                f.write(thumb_data.content)

            await reply_msg.edit_text("ᴜᴘʟᴏᴀᴅɪɴɢ...")
            return file_path, thumbnail_path, video_title

    except Exception as e:
        import traceback
        logging.error(f"Download error: {e}")
        await reply_msg.edit_text(f"❌ Error while downloading:\n<code>{traceback.format_exc()}</code>", parse_mode="html")
        return None, None, None


# --- Upload Video Function ---
async def upload_video(client, file_path, thumbnail_path, video_title, reply_msg, collection_channel_id, user_mention, user_id, message):
    file_size = os.path.getsize(file_path)
    uploaded = 0
    start_time = datetime.now()
    last_update_time = time.time()

    async def progress(current, total):
        nonlocal uploaded, last_update_time
        uploaded = current
        percentage = (current / total) * 100
        elapsed = (datetime.now() - start_time).total_seconds()

        if time.time() - last_update_time > 2:
            progress_text = format_progress_bar(
                filename=video_title,
                percentage=percentage,
                done=current,
                total_size=total,
                status="Uploading",
                eta=(total - current) / (current / elapsed) if current > 0 else 0,
                speed=current / elapsed if current > 0 else 0,
                elapsed=elapsed,
                user_mention=user_mention,
                user_id=user_id,
                aria2p_gid=""
            )
            try:
                await reply_msg.edit_text(progress_text)
                last_update_time = time.time()
            except Exception as e:
                logging.warning(f"Error updating progress message: {e}")

    # Send video to collection channel
    with open(file_path, 'rb') as file:
        collection_message = await client.send_video(
            chat_id=collection_channel_id,
            video=file,
            caption=f"✨ ᴛɪᴛʟᴇ: {video_title}\n👤 ᴅᴏᴡɴʟᴏᴀᴅᴇᴅ ʙʏ: {user_mention}\n📥 ᴜsᴇʀ ʟɪɴᴋ: tg://openmessage?user_id={user_id}",
            thumb=thumbnail_path,
            progress=progress
        )
        await client.copy_message(
            chat_id=message.chat.id,
            from_chat_id=collection_channel_id,
            message_id=collection_message.id
        )
        await message.delete()

    await reply_msg.delete()
    try:
        await message.reply_sticker("CAACAgUAAxkBAAKAEWcBqlNKFe0wAuORDYIlEXotOTuRAALhAQACrb-BNke3w36Xb2zoNgQ")
    except:
        pass

    os.remove(file_path)
    os.remove(thumbnail_path)
