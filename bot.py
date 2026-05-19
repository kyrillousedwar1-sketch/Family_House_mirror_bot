import asyncio
import mimetypes
import os
import shlex
import subprocess
from pathlib import Path

import aiohttp
from pyrogram import Client, filters
from pyrogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

# =========================
# Environment Variables
# =========================
API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")

if not API_ID or not API_HASH or not BOT_TOKEN:
    raise ValueError("Missing API_ID, API_HASH or BOT_TOKEN environment variables")

DOWNLOAD_DIR = Path("downloads")
DOWNLOAD_DIR.mkdir(exist_ok=True)

bot = Client(
    "leech_bot",
    api_id=int(API_ID),
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    in_memory=True,
)

user_thumbnails = {}


# =========================
# Helpers
# =========================
def main_menu_keyboard():
    keyboard = [
        [
            InlineKeyboardButton("ℹ️ شرح الأوامر", callback_data="help_info"),
            InlineKeyboardButton("🖼️ الـ Thumbnail الحالي", callback_data="show_thumb"),
        ],
        [
            InlineKeyboardButton("❌ مسح الـ Thumbnail", callback_data="clear_thumb"),
            InlineKeyboardButton("⚡ حالة السيرفر", callback_data="server_status"),
        ],
        [InlineKeyboardButton("📢 قناة المطور", url="https://t.me/YourChannel")],
    ]
    return InlineKeyboardMarkup(keyboard)


def is_video_file(file_path: str) -> bool:
    mime, _ = mimetypes.guess_type(file_path)
    return bool(mime and mime.startswith("video"))


async def download_file(url: str, output_path: str):
    timeout = aiohttp.ClientTimeout(total=3600)

    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.get(url) as response:
            if response.status != 200:
                raise Exception(f"Download failed with status {response.status}")

            with open(output_path, "wb") as file:
                async for chunk in response.content.iter_chunked(1024 * 1024):
                    file.write(chunk)


async def compress_video(input_file: str, output_file: str):
    command = [
        "ffmpeg",
        "-i",
        input_file,
        "-vcodec",
        "libx264",
        "-crf",
        "28",
        "-preset",
        "fast",
        output_file,
        "-y",
    ]

    process = await asyncio.create_subprocess_exec(
        *command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    _, stderr = await process.communicate()

    if process.returncode != 0:
        raise Exception(stderr.decode())


# =========================
# Commands
# =========================
@bot.on_message(filters.command("start"))
async def start_cmd(client, message: Message):
    welcome_text = (
        f"أهلاً بك يا {message.from_user.mention} في بوت الـ Leech & Mirror 🚀\n\n"
        "أرسل رابط مباشر أو ملف فيديو وسيتم ضغطه ورفعه تلقائيًا."
    )

    await message.reply_text(
        welcome_text,
        reply_markup=main_menu_keyboard(),
    )


@bot.on_callback_query()
async def handle_callbacks(client, callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    data = callback_query.data

    if data == "help_info":
        help_text = (
            "📌 دليل استخدام البوت\n\n"
            "• أرسل رابط مباشر للفيديو\n"
            "• أرسل صورة لحفظها كـ Thumbnail\n"
            "• أرسل ملفات فيديو ليتم ضغطها ورفعها"
        )

        keyboard = InlineKeyboardMarkup(
            [[InlineKeyboardButton("⬅️ رجوع", callback_data="back_main")]]
        )

        await callback_query.message.edit_text(help_text, reply_markup=keyboard)

    elif data == "back_main":
        await callback_query.message.edit_text(
            "القائمة الرئيسية ⚡",
            reply_markup=main_menu_keyboard(),
        )

    elif data == "show_thumb":
        thumb = user_thumbnails.get(user_id)

        if thumb and os.path.exists(thumb):
            await bot.send_photo(
                callback_query.message.chat.id,
                thumb,
                caption="الـ Thumbnail الحالي",
            )
        else:
            await callback_query.answer("لا يوجد Thumbnail محفوظ", show_alert=True)

    elif data == "clear_thumb":
        thumb = user_thumbnails.get(user_id)

        if thumb and os.path.exists(thumb):
            os.remove(thumb)
            user_thumbnails.pop(user_id, None)
            await callback_query.answer("تم حذف الـ Thumbnail", show_alert=True)
        else:
            await callback_query.answer("لا يوجد Thumbnail", show_alert=True)

    elif data == "server_status":
        await callback_query.answer("البوت يعمل بنجاح ✅", show_alert=True)


# =========================
# Thumbnail
# =========================
@bot.on_message(filters.photo)
async def save_thumbnail(client, message: Message):
    user_id = message.from_user.id

    thumb_path = DOWNLOAD_DIR / f"thumb_{user_id}.jpg"

    await message.download(file_name=str(thumb_path))

    user_thumbnails[user_id] = str(thumb_path)

    await message.reply_text("تم حفظ الـ Thumbnail بنجاح ✅")


# =========================
# Direct Links
# =========================
@bot.on_message(filters.text & filters.regex(r"^https?://"))
async def handle_links(client, message: Message):
    url = message.text.strip()
    user_id = message.from_user.id

    status = await message.reply_text("جاري تحميل الملف... ⏳")

    try:
        filename = url.split("/")[-1].split("?")[0] or "video.mp4"

        local_file = DOWNLOAD_DIR / filename
        compressed_file = DOWNLOAD_DIR / f"compressed_{filename}"

        await download_file(url, str(local_file))

        if is_video_file(str(local_file)):
            await status.edit("جاري ضغط الفيديو عبر FFmpeg... 🎞️")

            try:
                await compress_video(str(local_file), str(compressed_file))
                upload_file = compressed_file
                caption = "تم الضغط والرفع بنجاح ✅"
            except Exception:
                upload_file = local_file
                caption = "فشل الضغط، تم رفع الملف الأصلي ⚠️"
        else:
            upload_file = local_file
            caption = "الملف ليس فيديو، تم رفعه كمستند 📁"

        await status.edit("جاري الرفع إلى تيليجرام... 📤")

        thumb = user_thumbnails.get(user_id)

        if is_video_file(str(upload_file)):
            if thumb and os.path.exists(thumb):
                await message.reply_video(
                    video=str(upload_file),
                    thumb=thumb,
                    caption=caption,
                )
            else:
                await message.reply_video(
                    video=str(upload_file),
                    caption=caption,
                )
        else:
            await message.reply_document(
                document=str(upload_file),
                caption=caption,
            )

    except Exception as error:
        await message.reply_text(f"حدث خطأ ❌\n{str(error)}")

    finally:
        for file in DOWNLOAD_DIR.iterdir():
            if file.is_file() and not file.name.startswith("thumb_"):
                try:
                    file.unlink()
                except Exception:
                    pass

        await status.delete()


# =========================
# Torrent Files
# =========================
@bot.on_message(filters.document)
async def handle_torrent(client, message: Message):
    if not message.document:
        return

    file_name = message.document.file_name or ""

    if file_name.endswith(".torrent"):
        await message.reply_text(
            "تم استقبال ملف التورنت ✅\nلكن نظام تحميل التورنت الكامل غير مضاف حاليًا."
        )


if __name__ == "__main__":
    print("Bot Started...")
    bot.run()
