import re 
from datetime import datetime
import logging
import asyncio
import random
import string
import os
from pymongo import MongoClient
from dotenv import load_dotenv
from pyrogram import Client, filters
from pyrogram.enums import ChatMemberStatus
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import FloodWait, UserIsBlocked, InputUserDeactivated
from os import environ
import time
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from status import format_progress_bar  # Assuming this is a custom module
from video import download_video, upload_video  # Assuming these are custom modules
from database.database import present_user, add_user, full_userbase, del_user, db_verify_status, db_update_verify_status  # Assuming these are custom modules
from shortzy import Shortzy  # Assuming this is a custom module
from pymongo.errors import DuplicateKeyError
from web import keep_alive
from config import *

load_dotenv('config.env', override=True)

logging.basicConfig(level=logging.INFO)

ADMINS = list(map(int, os.environ.get('ADMINS', '7064434873').split()))
if not ADMINS:
    logging.error("ADMINS variable is missing! Exiting now")
    exit(1)
    
api_id = os.environ.get('TELEGRAM_API', '')
if not api_id:
    logging.error("TELEGRAM_API variable is missing! Exiting now")
    exit(1)

api_hash = os.environ.get('TELEGRAM_HASH', '')
if not api_hash:
    logging.error("TELEGRAM_HASH variable is missing! Exiting now")
    exit(1)
    
bot_token = os.environ.get('BOT_TOKEN', '')
if not bot_token:
    logging.error("BOT_TOKEN variable is missing! Exiting now")
    exit(1)
dump_id = os.environ.get('DUMP_CHAT_ID', '')
if not dump_id:
    logging.error("DUMP_CHAT_ID variable is missing! Exiting now")
    exit(1)
else:
    dump_id = int(dump_id)

fsub_id = os.environ.get('FSUB_ID', '')
if not fsub_id:
    logging.error("FSUB_ID variable is missing! Exiting now")
    exit(1)
else:
    fsub_id = int(fsub_id)


mongo_url = os.environ.get('MONGO_URL', 'mongodb+srv://cphdlust:cphdlust@cphdlust.ydeyw.mongodb.net/?retryWrites=true&w=majority&')
client = MongoClient(mongo_url)
db = client['cphdlust']
users_collection = db['users']

def extract_links(text):
    url_pattern = r'(https?://[^\s]+)'  # Regex to capture http/https URLs
    links = re.findall(url_pattern, text)
    return links

def save_user(user_id, username):
    try:
        existing_user = users_collection.find_one({'user_id': user_id})
        if existing_user is None:
            users_collection.insert_one({'user_id': user_id, 'username': username})
            logging.info(f"Saved new user {username} with ID {user_id} to the database.")
        else:
            users_collection.update_one({'user_id': user_id}, {'$set': {'username': username}})
            logging.info(f"Updated user {username} with ID {user_id} in the database.")
    except DuplicateKeyError as e:
        logging.error(f"DuplicateKeyError: {e}")

app = Client("my_bot", api_id=api_id, api_hash=api_hash, bot_token=bot_token)

async def get_shortlink(url, api, link):
    shortzy = Shortzy(api_key=api, base_site=url)
    link = await shortzy.convert(link)
    return link

def get_exp_time(seconds):
    periods = [('days', 86400), ('hours', 3600), ('mins', 60), ('secs', 1)]
    result = ''
    for period_name, period_seconds in periods:
        if seconds >= period_seconds:
            period_value, seconds = divmod(seconds, period_seconds)
            result += f'{int(period_value)}{period_name} '
    return result

def get_readable_time(seconds: int) -> str:
    count = 0
    up_time = ""
    time_list = []
    time_suffix_list = ["s", "m", "h", "days"]
    while count < 4:
        count += 1
        remainder, result = divmod(seconds, 60) if count < 3 else divmod(seconds, 24)
        if seconds == 0 and remainder == 0:
            break
        time_list.append(int(result))
        seconds = int(remainder)
    hmm = len(time_list)
    for x in range(hmm):
        time_list[x] = str(time_list[x]) + time_suffix_list[x]
    if len(time_list) == 4:
        up_time += f"{time_list.pop()}, "
    time_list.reverse()
    up_time += ":".join(time_list)
    return up_time

async def get_verify_status(user_id):
    verify = await db_verify_status(user_id)
    return verify

async def update_verify_status(user_id, verify_token="", is_verified=False, verified_time=0, link=""):
    current = await db_verify_status(user_id)
    current['verify_token'] = verify_token
    current['is_verified'] = is_verified
    current['verified_time'] = verified_time
    current['link'] = link
    await db_update_verify_status(user_id, current)

@app.on_message(filters.command("start"))
async def start_command(client, message):
    user_id = message.from_user.id
    user_mention = message.from_user.mention
    
    # Check if user is present
    if not await present_user(user_id):
        try:
            await add_user(user_id)
            logging.info(f"Added user {user_id} to the database")
        except Exception as e:
            logging.error(f"Failed to add user {user_id} to the database: {e}")

    # Send sticker and delete it after 2 seconds
    sticker_message = await message.reply_sticker("CAACAgQAAxkBAAKAC2cBpyr7k-jZ5tWcbE4r2DQO5VK2AAIHEQAC92SxUtIJGuU0-EVmNgQ")
    await asyncio.sleep(1.8)
    await sticker_message.delete()

    # Get verification status
    verify_status = await db_verify_status(user_id)
    logging.info(f"Verify status for user {user_id}: {verify_status}")

    # Check verification expiration
    if verify_status["is_verified"] and VERIFY_EXPIRE < (time.time() - verify_status["verified_time"]):
        await db_update_verify_status(user_id, {**verify_status, 'is_verified': False})
        verify_status['is_verified'] = False
        logging.info(f"Verification expired for user {user_id}")

    text = message.text
    if "verify_" in text:
        _, token = text.split("_", 1)
        logging.info(f"Extracted token: {token}")
        if verify_status["verify_token"] != token:
            logging.warning(f"Invalid or expired token for user {user_id}")
            return await message.reply("Your token is invalid or expired. Try again by clicking /start.")
        await db_update_verify_status(user_id, {**verify_status, 'is_verified': True, 'verified_time': time.time()})
        logging.info(f"User {user_id} verified successfully")
        return await message.reply("✅ Your token has been successfully verified and is valid for the next 12 hours ⏳.")

    if verify_status["is_verified"]:
        logging.info(f"User {user_id} is verified")
        reply_message = (
        f"🌟 Welcome to the Ultimate TeraBox Downloader Bot, {user_mention}!\n\n"
        "🚀 **Why Choose This Bot?**\n"
        "- **Unmatched Speed**: Experience the fastest and most powerful TeraBox downloader on Telegram. ⚡\n"
        "- **100% Free Forever**: No hidden fees or subscriptions—completely free for everyone! 🆓\n"
        "- **Seamless Downloads**: Easily download TeraBox files and have them sent directly to you. 🎥📁\n"
        "- **24/7 Availability**: Access the bot anytime, anywhere, without downtime. ⏰\n\n"
        "🎯 **How It Works**\n"
        "Simply send a TeraBox link, and let the bot handle the rest. It's quick, easy, and reliable! 🚀\n\n"
        "💎 **Your Ultimate Telegram Tool**—crafted to make your experience effortless and enjoyable.\n\n"
        "Join our growing community to discover more features and stay updated! 👇"
        )
        join_button = InlineKeyboardButton("Join ❤️🚀", url="https://t.me/Xstream_links2")
        developer_button = InlineKeyboardButton("Developer ⚡️", url="https://t.me/Xstream_Links2")
        reply_markup = InlineKeyboardMarkup([[join_button, developer_button]])
        await message.reply_text(reply_message, reply_markup=reply_markup)
    else:
        logging.info(f"User {user_id} is not verified or has expired token")
        if IS_VERIFY:
            token = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
            logging.info(f"Generated token: {token}")
            link = await get_shortlink(SHORTLINK_URL, SHORTLINK_API, f'https://t.me/happylassan_bot?start=verify_{token}')
            await db_update_verify_status(user_id, {**verify_status, 'verify_token': token, 'link': link})
            message_text = (
                "🚨 Token Expired!\n\n"
                f"Token Timeout: {get_exp_time(VERIFY_EXPIRE)}\n\n"
                "It looks like your access token has expired. Don't worry—you can easily refresh it to continue using the bot.?\n\n"
                "🔑 What is this token?\n\n"
                "This token is your access pass to the bot's premium features. By completing a simple ad process, you'll unlock 12 hours of uninterrupted access to all services. "
                "No hidden fees, no catches—just seamless functionality! 🌟\n\n"
                "👉 Tap the button below to refresh your token and get started instantly. For guidance, check out our step-by-step tutorial.\n\n"
                "💡 Why tokens?\n\n"
                "Tokens help us keep the bot free for everyone by supporting operational costs through a quick ad process. Thank you for your understanding and support! ❤️"
                )
            token_button = InlineKeyboardButton("Get Token 🔗", url=link)
            tutorial_button = InlineKeyboardButton("How to Verify 🎥", url="https://t.me/AR_File_To_Link_Bot/?start=MzA2OTMxOTgxMzI2MzkwOTAwLzgxOTQ3NjgzMg")
            reply_markup = InlineKeyboardMarkup([[token_button], [tutorial_button]])
            await message.reply_text(message_text, reply_markup=reply_markup)
        else:
            logging.warning(f"Verification is not enabled or user {user_id} does not need verification")


@app.on_message(filters.command('broadcast') & filters.user(ADMINS))
async def broadcast_command(client, message):
    if message.reply_to_message:
        query = await full_userbase()
        broadcast_msg = message.reply_to_message
        total = 0
        successful = 0
        blocked = 0
        deleted = 0
        unsuccessful = 0
        
        pls_wait = await message.reply("<i>Broadcasting Message.. This will Take Some Time</i>")
        for chat_id in query:
            try:
                await broadcast_msg.copy(chat_id)
                successful += 1
            except FloodWait as e:
                await asyncio.sleep(e.x)
                await broadcast_msg.copy(chat_id)
                successful += 1
            except UserIsBlocked:
                await del_user(chat_id)
                blocked += 1
            except InputUserDeactivated:
                await del_user(chat_id)
                deleted += 1
            except:
                unsuccessful += 1
                pass
            total += 1
        
        status = f"""<b><u>Broadcast Completed</u></b>

Total Users: <code>{total}</code>
Successful: <code>{successful}</code>
Blocked Users: <code>{blocked}</code>
Deleted Accounts: <code>{deleted}</code>
Unsuccessful: <code>{unsuccessful}</code>"""
        
        await pls_wait.edit(status)
    else:
        msg = await message.reply("Please reply to a message to broadcast it.")
        await asyncio.sleep(8)
        await msg.delete()

@app.on_message(filters.command("stats") & filters.user(ADMINS))
async def stats_command(client, message):
    total_users = users_collection.count_documents({})
    verified_users = users_collection.count_documents({"verify_status.is_verified": True})
    unverified_users = total_users - verified_users

    status = f"""<b>📊<u>Verification Statistics</u></b>

👥 Total Users: <code>{total_users}</code>
✅ Verified Users: <code>{verified_users}</code>
❌ Unverified Users: <code>{unverified_users}</code>"""

    await message.reply(status)   

@app.on_message(filters.command("check"))
async def check_command(client, message):
    user_id = message.from_user.id

    verify_status = await db_verify_status(user_id)
    logging.info(f"Verify status for user {user_id}: {verify_status}")

    if verify_status['is_verified']:
        expiry_time = get_exp_time(VERIFY_EXPIRE - (time.time() - verify_status['verified_time']))
        await message.reply(f"✅ Your token has been successfully verified and is valid for {expiry_time}.")
    else:
        await message.reply("❌ Your token is either not verified or has expired. Please use /start to generate a new token and verify it. 🔄...")

async def is_user_member(client, user_id):
    try:
        member = await client.get_chat_member(fsub_id, user_id)
        logging.info(f"User {user_id} membership status: {member.status}")
        if member.status in [ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]:
            return True
        else:
            return False
    except Exception as e:
        logging.error(f"Error checking membership status for user {user_id}: {e}")
        return False

def is_terabox_link(link):
    keywords = ["terabox", "terafileshare", "1024tera", "terasharelink", "xnxx"]
    return any(keyword in link.lower() for keyword in keywords)

valid_domains = [
    'terabox.com', 'nephobox.com', '4funbox.com', 'mirrobox.com', 'terabox.link', 
    'momerybox.com', 'teraboxapp.com', 'terafileshare.com', '1024tera.com', 'xnxx', 
    'terabox.app', 'gibibox.com', 'goaibox.com', 'terasharelink.com', 'teraboxlink.com',
    'www.terabox.app', 'terabox.fun', 'www.terabox.com', 'www.1024tera.com', 'teraboxshare.com',
    'www.mirrobox.com', 'www.nephobox.com', 'freeterabox.com', 'www.freeterabox.com', '4funbox.co'
]

def is_valid_domain(link):
    """Check if the link belongs to any valid domain."""
    return any(domain in link for domain in valid_domains)

@app.on_message(filters.text)
async def handle_message(client, message: Message):
    user_id = message.from_user.id
    if not await present_user(user_id):
        try:
            await add_user(user_id)
        except Exception as e:
            logging.error(f"Failed to add user {user_id} to the database: {e}")

    user_mention = message.from_user.mention
    
    verify_status = await db_verify_status(user_id)

    # Check verification expiration
    if verify_status["is_verified"] and VERIFY_EXPIRE < (time.time() - verify_status["verified_time"]):
        await db_update_verify_status(user_id, {**verify_status, 'is_verified': False})
        verify_status['is_verified'] = False
        logging.info(f"Verification expired for user {user_id}")

    if not verify_status["is_verified"]:
        await message.reply_text("🔒 To access the bot, please verify your identity. Click /start to begin the verification process..")
        return

    is_member = await is_user_member(client, user_id)

    if not is_member:
        join_button = InlineKeyboardButton("Join ❤️🚀", url="https://t.me/Xstream_links2")
        reply_markup = InlineKeyboardMarkup([[join_button]])
        await message.reply_text("✳️ To keep things secure and make sure only real users are accessing the bot, please subscribe to the channel below first.", reply_markup=reply_markup)
        return

    links = extract_links(message.text)
    
    if not links:
        await message.reply_text("Please send a valid link.")
        return

    for terabox_link in links:
        if not is_terabox_link(terabox_link):
            await message.reply_text(f"{terabox_link} is not a valid Terabox link.")
            continue
            
    reply_msg = await message.reply_text("🔄 Retrieving your TeraBox video your content is on the way, just a moment!")

    try:
        file_path, thumbnail_path, video_title = await download_video(terabox_link, reply_msg, user_mention, user_id)
        await upload_video(client, file_path, thumbnail_path, video_title, reply_msg, dump_id, user_mention, user_id, message)
    except Exception as e:
        logging.error(f"Error handling message: {e}")
        await handle_video_download_failure(reply_msg, terabox_link)

async def handle_video_download_failure(reply_msg, url):
    """Handle cases when API request fails by showing a 'Watch Online' button."""
    watch_online_button = InlineKeyboardButton(
        "📺 Watch Online", 
        web_app=WebAppInfo(url=f"https://terabox-watch.netlify.app/?url={url}")
    )

    watch_online_2 = InlineKeyboardButton(
        "📺 Watch Online (API 2)", 
        web_app=WebAppInfo(url=f"https://terabox-watch.netlify.app/api2.html?url={url}")
    )
    
    reply_markup = InlineKeyboardMarkup([
        [watch_online_button],  # Button 1 in the first row
        [watch_online_2]   # Button 2 in the second row
    ])
    await reply_msg.edit_text(
        "⚠️ **API Request Failed!**\n\n"
        "The download link could not be retrieved at this time. However, if this is a TeraBox link, you can still watch the video online by clicking the button below ⬇️:",
        reply_markup=reply_markup
    )

if __name__ == "__main__":
    keep_alive()
    app.run()
