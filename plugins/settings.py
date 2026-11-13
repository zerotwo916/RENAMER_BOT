import os
from pyrogram import Client, filters
from pyrogram.types import Message
from motor.motor_asyncio import AsyncIOMotorClient
import config

db_client = AsyncIOMotorClient(config.MONGO_DB_URI)
db = db_client["telegram_renamer_bot"]
users_col = db["user_settings"]

async def get_user_data(user_id: int):
    data = await users_col.find_one({"_id": user_id})
    return data or {}

async def update_user_data(user_id: int, key: str, value):
    await users_col.update_one(
        {"_id": user_id},
        {"$set": {key: value}},
        upsert=True
    )

@Client.on_message(filters.command("start"))
async def start_command(client: Client, message: Message):
    await message.reply_text("Welcome to your Renamer Bot! Send any video or document file to rename it using your saved metadata and settings.")

@Client.on_message(filters.command("help"))
async def help_command(client: Client, message: Message):
    await message.reply_text(
        "**Available Commands:**\n"
        "/set_thumb - Save custom thumbnail image\n"
        "/viewthumb - View currently saved thumbnail\n"
        "/settitle - Set custom title metadata\n"
        "/setaudio - Set custom audio track handling\n"
        "/setsubtitle - Set custom subtitle track handling\n"
        "/setvideo - Set custom video track handling\n"
        "/setartist - Set custom artist metadata\n"
        "/setauthor - Set custom author metadata"
    )

@Client.on_message(filters.command("set_thumb"))
async def set_thumb(client: Client, message: Message):
    photo = message.photo or (message.reply_to_message and message.reply_to_message.photo)
    if not photo:
        await message.reply_text("Please send an image with the /set_thumb command or reply to a photo.")
        return
    
    file_id = photo.file_id
    await update_user_data(message.from_user.id, "thumbnail", file_id)
    await message.reply_text("Custom thumbnail saved successfully!")

@Client.on_message(filters.command("viewthumb"))
async def view_thumb(client: Client, message: Message):
    user_data = await get_user_data(message.from_user.id)
    thumb = user_data.get("thumbnail")
    
    if not thumb:
        await message.reply_text("No custom thumbnail found. Use /set_thumb to save one.")
        return
        
    await client.send_photo(message.chat.id, photo=thumb, caption="Your saved custom thumbnail:")

@Client.on_message(filters.command("settitle"))
async def set_title(client: Client, message: Message):
    if len(message.command) < 2:
        await message.reply_text("Please provide a title! Example: /settitle Ongoing_AnimeYaro")
        return
        
    title = " ".join(message.command[1:])
    await update_user_data(message.from_user.id, "title", title)
    await message.reply_text(f"Title successfully set to: {title}")

@Client.on_message(filters.command("setaudio"))
async def set_audio(client: Client, message: Message):
    if len(message.command) < 2:
        await message.reply_text("Please provide audio track details!")
        return
        
    audio = " ".join(message.command[1:])
    await update_user_data(message.from_user.id, "audio", audio)
    await message.reply_text(f"Audio track setting updated to: {audio}")

@Client.on_message(filters.command("setsubtitle"))
async def set_subtitle(client: Client, message: Message):
    if len(message.command) < 2:
        await message.reply_text("Please provide subtitle details!")
        return
        
    subtitle = " ".join(message.command[1:])
    await update_user_data(message.from_user.id, "subtitle", subtitle)
    await message.reply_text(f"Subtitle track setting updated to: {subtitle}")

@Client.on_message(filters.command("setvideo"))
async def set_video(client: Client, message: Message):
    if len(message.command) < 2:
        await message.reply_text("Please provide video track details!")
        return
        
    video = " ".join(message.command[1:])
    await update_user_data(message.from_user.id, "video", video)
    await message.reply_text(f"Video track setting updated to: {video}")

@Client.on_message(filters.command("setartist"))
async def set_artist(client: Client, message: Message):
    if len(message.command) < 2:
        await message.reply_text("Please provide artist name!")
        return
        
    artist = " ".join(message.command[1:])
    await update_user_data(message.from_user.id, "artist", artist)
    await message.reply_text(f"Artist successfully set to: {artist}")

@Client.on_message(filters.command("setauthor"))
async def set_author(client: Client, message: Message):
    if len(message.command) < 2:
        await message.reply_text("Please provide author name!")
        return
        
    author = " ".join(message.command[1:])
    await update_user_data(message.from_user.id, "author", author)
    await message.reply_text(f"Author successfully set to: {author}")

@Client.on_message(filters.document | filters.video)
async def rename_and_upload_file(client: Client, message: Message):
    user_id = message.from_user.id
    user_data = await get_user_data(user_id)
    
    custom_title = user_data.get("title", "AnimeYaro")
    thumb = user_data.get("thumbnail")

    status_msg = await message.reply_text("📥 Downloading your file...")

    # Download file locally
    file_path = await message.download()
    
    file_ext = os.path.splitext(file_path)[1]
    new_filename = f"{custom_title}{file_ext}"
    new_file_path = os.path.join("downloads", new_filename)
    os.makedirs("downloads", exist_ok=True)
    os.rename(file_path, new_file_path)

    await status_msg.edit_text("📤 Uploading renamed file...")
    
    if thumb:
        await client.send_document(
            chat_id=message.chat.id,
            document=new_file_path,
            thumb=thumb,
            caption=f"@{custom_title}"
        )
    else:
        await client.send_document(
            chat_id=message.chat.id,
            document=new_file_path,
            caption=f"@{custom_title}"
        )

    if os.path.exists(new_file_path):
        os.remove(new_file_path)
        
    await status_msg.delete()
