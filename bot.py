import os
import subprocess
from pyrogram import Client, filters
from motor.motor_asyncio import AsyncIOMotorClient

# Load credentials from Railway Environment Variables
API_ID = int(os.environ.get("API_ID", 0))
API_HASH = os.environ.get("API_HASH")
BOT_TOKEN = os.environ.get("BOT_TOKEN")
MONGO_DB_URL = os.environ.get("MONGO_DB_URL")

# Connect to MongoDB
db_client = AsyncIOMotorClient(MONGO_DB_URL)
db = db_client["telegram_rename_bot"]
thumbs_col = db["thumbnails"]

app = Client("telegram_rename_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

@app.on_message(filters.command(["start", "help"]))
async def help_menu(client, message):
    menu_text = (
        "🤖 **AIOM Telegram Rename & Metadata Bot**\n\n"
        "**Features & How to Use:**\n"
        "• **Permanent Thumbnail**: Send any photo with `/set_thumb` in the caption to save it to MongoDB.\n"
        "• **Custom Metadata**: Send a video with custom tags in the caption using this format:\n\n"
        "  `title: Your Custom Title`\n"
        "  `artist: Your Name / Studio`\n"
        "  `audio: Audio Track Name`\n"
        "  `subtitle: Subtitle Language`\n\n"
        "*(You can leave any of these lines blank or omit them entirely if you don't want to change them!)*\n\n"
        "📌 **Commands:**\n"
        "• `/start` or `/help` - Show this menu\n"
        "• `/set_thumb` - Send with a photo to save your thumbnail"
    )
    await message.reply_text(menu_text)

@app.on_message(filters.photo & filters.caption & filters.regex("/set_thumb"))
async def save_thumbnail(client, message):
    user_id = message.from_user.id
    photo_id = message.photo.file_id
    
    # Save or update thumbnail file_id in MongoDB permanently
    await thumbs_col.update_one(
        {"user_id": user_id},
        {"$set": {"thumb_file_id": photo_id}},
        upsert=True
    )
    await message.reply_text("✅ **Thumbnail saved permanently in MongoDB!** Now send any video file.")

@app.on_message(filters.document | filters.video)
async def process_video(client, message):
    user_id = message.from_user.id
    status_msg = await message.reply_text("📥 Downloading file...")
    file_path = await message.download()
    
    output_file = f"clean_{os.path.basename(file_path)}"
    
    # Parse caption for custom metadata (title, artist, audio, subtitle)
    custom_meta = {}
    caption = message.caption or ""
    
    for line in caption.split("\n"):
        if ":" in line:
            key, val = line.split(":", 1)
            key = key.strip().lower()
            val = val.strip()
            # Only accept supported keys if they have text
            if key in ["title", "artist", "audio", "subtitle"] and val:
                custom_meta[key] = val

    # Build FFmpeg command dynamically
    cmd = ["ffmpeg", "-i", file_path, "-map_metadata", "-1"]
    
    # Add custom metadata tags only if provided by the user
    for key, value in custom_meta.items():
        cmd.extend(["-metadata", f"{key}={value}"])
        
    cmd.extend(["-c", "copy", output_file])
    
    subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    
    await status_msg.edit_text("⚙️ Processing metadata & thumbnail...")
    
    # Retrieve user's custom thumbnail from MongoDB
    user_data = await thumbs_col.find_one({"user_id": user_id})
    thumb_path = None
    
    if user_data and "thumb_file_id" in user_data:
        thumb_path = await client.download_media(user_data["thumb_file_id"])
    
    await status_msg.edit_text("📤 Sending clean video...")
    await client.send_video(
        chat_id=message.chat.id,
        video=output_file,
        thumb=thumb_path,
        supports_streaming=True
    )
    
    # Cleanup temporary local storage files
    os.remove(file_path)
    if os.path.exists(output_file):
        os.remove(output_file)
    if thumb_path and os.path.exists(thumb_path):
        os.remove(thumb_path)
    await status_msg.delete()

app.run()
