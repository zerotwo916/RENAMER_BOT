import os
import subprocess
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, Message
from motor.motor_asyncio import AsyncIOMotorClient
from config import Config

db_client = AsyncIOMotorClient(Config.MONGO_DB_URL)
db = db_client["telegram_rename_bot"]
thumbs_col = db["thumbnails"]

USER_DATA = {}

@Client.on_message(filters.command(["start", "help"]))
async def help_menu(client: Client, message: Message):
    menu_text = (
        "🤖 **AIOM Telegram Rename & Metadata Bot**\n\n"
        "**Features & How to Use:**\n"
        "• **Permanent Thumbnail**: Send any photo with `/set_thumb` in the caption to save it to MongoDB.\n"
        "• **Interactive Rename**: Send any video/document file to view its info and rename it.\n"
        "• **Custom Metadata**: Type title, artist, audio, or subtitle tags when renaming.\n\n"
        "📌 **Commands:**\n"
        "• `/start` or `/help` - Show this menu\n"
        "• `/set_thumb` - Reply to a photo to save your thumbnail"
    )
    await message.reply_text(menu_text)

@Client.on_message(filters.photo & filters.caption & filters.regex("/set_thumb"))
async def save_thumbnail(client: Client, message: Message):
    user_id = message.from_user.id
    photo_id = message.photo.file_id
    await thumbs_col.update_one(
        {"user_id": user_id},
        {"$set": {"thumb_file_id": photo_id}},
        upsert=True
    )
    await message.reply_text("✅ **Thumbnail saved permanently in MongoDB!**")

@Client.on_message((filters.document | filters.video) & filters.private)
async def incoming_file(client: Client, message: Message):
    user_id = message.from_user.id
    file = message.document or message.video
    
    USER_DATA[user_id] = {
        "message": message,
        "file_name": file.file_name or "video.mkv",
        "file_size": file.file_size
    }
    
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📝 Rename", callback_data="start_rename"),
            InlineKeyboardButton("❌ Cancel", callback_data="cancel_rename")
        ]
    ])
    
    size_mb = round(file.file_size / (1024 * 1024), 2)
    ext = os.path.splitext(file.file_name)[1] if file.file_name else "mkv"
    
    info_text = (
        f"📁 **Media Info :**\n\n"
        f"🔹 **File Name :** `{file.file_name}`\n"
        f"📦 **File Size :** `{size_mb} MB`\n"
        f"🎞 **File Extension :** `{ext}`\n\n"
        f"Please Enter The New Filename."
    )
    
    await message.reply_text(info_text, reply_markup=keyboard)

@Client.on_callback_query(filters.regex("cancel_rename"))
async def cancel_callback(client: Client, query: CallbackQuery):
    user_id = query.from_user.id
    if user_id in USER_DATA:
        del USER_DATA[user_id]
    await query.message.edit_text("❌ **Operation cancelled.**")

@Client.on_callback_query(filters.regex("start_rename"))
async def rename_callback(client: Client, query: CallbackQuery):
    await query.message.edit_text(
        "✍️ **Send me the new filename or custom metadata tags now!**\n\n"
        "Example format:\n"
        "`My_Custom_Episode_01.mkv`\n\n"
        "Or with custom metadata:\n"
        "`title: Episode 1`\n`artist: Studio`"
    )

@Client.on_message(filters.text & filters.private)
async def process_custom_rename(client: Client, message: Message):
    user_id = message.from_user.id
    if user_id not in USER_DATA:
        return
        
    original_msg = USER_DATA[user_id]["message"]
    text_input = message.text.strip()
    
    # Extract first line as filename if multiline metadata is provided
    lines = text_input.split("\n")
    new_filename = lines[0].strip()
    
    status_msg = await message.reply_text("📥 Downloading file from Telegram...")
    file_path = await original_msg.download()
    
    ext = os.path.splitext(USER_DATA[user_id]["file_name"])[1] or ".mkv"
    if not new_filename.endswith(ext):
        new_filename += ext
        
    output_file = new_filename
    
    # Parse custom metadata tags
    custom_meta = {}
    for line in lines[1:]:
        if ":" in line:
            key, val = line.split(":", 1)
            key = key.strip().lower()
            val = val.strip()
            if key in ["title", "artist", "audio", "subtitle"] and val:
                custom_meta[key] = val

    cmd = ["ffmpeg", "-i", file_path, "-map_metadata", "-1"]
    for key, value in custom_meta.items():
        cmd.extend(["-metadata", f"{key}={value}"])
    cmd.extend(["-c", "copy", output_file])
    
    subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    
    await status_msg.edit_text("⚙️ Processing metadata & thumbnail...")
    
    user_data = await thumbs_col.find_one({"user_id": user_id})
    thumb_path = None
    if user_data and "thumb_file_id" in user_data:
        thumb_path = await client.download_media(user_data["thumb_file_id"])
        
    await status_msg.edit_text("📤 Uploading renamed video...")
    await client.send_video(
        chat_id=message.chat.id,
        video=output_file,
        thumb=thumb_path,
        supports_streaming=True,
        caption=f"✅ **Renamed to:** `{output_file}`"
    )
    
    os.remove(file_path)
    if os.path.exists(output_file):
        os.remove(output_file)
    if thumb_path and os.path.exists(thumb_path):
        os.remove(thumb_path)
    await status_msg.delete()
    del USER_DATA[user_id]
