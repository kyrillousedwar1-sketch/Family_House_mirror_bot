import os
import asyncio
import pyrogram
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
import aiohttp
import qbittorrentapi
import subprocess

# إعدادات البوت الأساسية من متغيرات البيئة (Environment Variables)
API_ID = int(os.environ.get("API_ID", 0))
API_HASH = os.environ.get("API_HASH", "")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")

bot = Client("leech_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# قاموس مؤقت لحفظ الثمنيل الخاص بكل مستخدم
user_thumbnails = {}

# دالة لإنشاء لوحة الأزرار المنبثقة (القائمة الرئيسية)
def main_menu_keyboard():
    keyboard = [
        [
            InlineKeyboardButton("ℹ️ شرح الأوامر", callback_data="help_info"),
            InlineKeyboardButton("🖼️ الـ Thumbnail الحالي", callback_data="show_thumb")
        ],
        [
            InlineKeyboardButton("❌ مسح الـ Thumbnail", callback_data="clear_thumb"),
            InlineKeyboardButton("⚡ حالة السيرفر", callback_data="server_status")
        ],
        [
            InlineKeyboardButton("📢 قناة المطور", url="https://t.me/YourChannel")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

# عند إرسال /start تظهر النافذة المنبثقة بالأزرار
@bot.on_message(filters.command("start"))
async def start_cmd(client, message: Message):
    welcome_text = (
        f"أهلاً بك يا {message.from_user.mention} في بوت الـ Leech & Mirror! 🚀\n\n"
        "يمكنك استخدام الأزرار بالأسفل كقائمة منبثقة للتحكم بالبوت ومعرفة الميزات."
    )
    await message.reply_text(welcome_text, reply_markup=main_menu_keyboard())

# معالجة الضغط على الأزرار المنبثقة (Callback Queries)
@bot.on_callback_query()
async def handle_callbacks(client, callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    data = callback_query.data

    if data == "help_info":
        help_text = (
            "📌 **دليل استخدام البوت:**\n\n"
            "1️⃣ **الروابط المباشرة:** أرسل أي رابط مباشر ليقوم البوت بتحميله وضغطه ورفعه فيديو.\n"
            "2️⃣ **التورنت:** أرسل ملف `.torrent` لبدء التحميل.\n"
            "3️⃣ **الـ Thumbnail:** أرسل أي صورة كـ (صورة عادية وليس ملف) وسيتم اعتمادها كغلاف للفيديوهات المرفوعة."
        )
        back_keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ عودة للقائمة الرئيسية", callback_data="back_main")]])
        await callback_query.message.edit_text(help_text, reply_markup=back_keyboard)
    
    elif data == "back_main":
        welcome_text = "قائمة التحكم المنبثقة للبوت: ⚡"
        await callback_query.message.edit_text(welcome_text, reply_markup=main_menu_keyboard())

    elif data == "show_thumb":
        thumb = user_thumbnails.get(user_id, None)
        if thumb and os.path.exists(thumb):
            await callback_query.answer("جاري إرسال الـ Thumbnail الخاص بك...", show_alert=False)
            await bot.send_photo(chat_id=callback_query.message.chat.id, photo=thumb, caption="هذا هو الغلاف الحالي لملفاتك.")
        else:
            await callback_query.answer("⚠️ لم تقم بتعيين Thumbnail مخصص بعد!", show_alert=True)

    elif data == "clear_thumb":
        thumb = user_thumbnails.get(user_id, None)
        if thumb and os.path.exists(thumb):
            os.remove(thumb)
            user_thumbnails.pop(user_id, None)
            await callback_query.answer("🗑️ تم حذف الـ Thumbnail بنجاح!", show_alert=True)
        else:
            await callback_query.answer("لا يوجد Thumbnail محفوط لحذفه.", show_alert=True)

    elif data == "server_status":
        await callback_query.answer("🖥️ السيرفر يعمل بكفاءة على Railway!", show_alert=True)

# استقبال الـ Thumbnail
@bot.on_message(filters.photo)
async def save_thumbnail(client, message: Message):
    user_id = message.from_user.id
    thumb_path = f"thumb_{user_id}.jpg"
    await message.download(file_name=thumb_path)
    user_thumbnails[user_id] = thumb_path
    await message.reply_text("تم حفظ الصورة كـ Thumbnail بنجاح! 🎉")

# التعامل مع الروابط المباشرة والـ Leech/Compression
@bot.on_message(filters.text & filters.regex(r'^https?://'))
async def handle_links(client, message: Message):
    url = message.text
    user_id = message.from_user.id
    status = await message.reply_text("جاري تحميل الملف المباشر...")
    
    local_filename = url.split("/")[-1] or "video.mp4"
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                with open(local_filename, 'wb') as f:
                    f.write(await response.read())
            else:
                await status.edit("فشل تحميل الرابط المباشر.")
                return

    await status.edit("تم التحميل. جاري فحص الملف وضغطه عبر FFmpeg...")
    
    compressed_filename = f"compressed_{local_filename}"
    ffmpeg_cmd = f"ffmpeg -i {local_filename} -vcodec libx264 -crf 28 -preset fast {compressed_filename} -y"
    
    process = subprocess.Popen(ffmpeg_cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    process.wait()

    await status.edit("جاري الرفع إلى تليجرام...")
    
    thumb = user_thumbnails.get(user_id, None)
    
    if os.path.exists(compressed_filename):
        await message.reply_video(video=compressed_filename, thumb=thumb, caption="تم الضغط والرفع بنجاح!")
        os.remove(compressed_filename)
    else:
        await message.reply_document(document=local_filename, thumb=thumb, caption="تم رفع الملف الأصلي (فشل الضغط أو ليس فيديو).")
    
    if os.path.exists(local_filename):
        os.remove(local_filename)
    await status.delete()

@bot.on_message(filters.document & filters.document.file_name.endswith(".torrent"))
async def handle_torrent(client, message: Message):
    await message.reply_text("تم استقبال ملف التورنت وجاري تحضيره للـ Leech... ⏳")

if __name__ == "__main__":
    bot.run()
