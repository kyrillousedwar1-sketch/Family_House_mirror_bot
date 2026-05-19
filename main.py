import os
import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message
import yt_dlp
from config import *

app = Client(
    "FamilyHouseBot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

# دالة التحميل المتقدمة والمحسنة لزيادة السرعة ودعم كافة المواقع
def download_video(url):
    ydl_opts = {
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best', # أفضل صيغة مدمجة
        'outtmpl': 'downloads/%(title)s.%(ext)s',
        'restrictfilenames': True,
        'noplaylist': True,
        'nocheckcertificate': True,
        'ignoreerrors': True,
        'logtostderr': False,
        'quiet': True,
        'no_warnings': True,
        'external_downloader': 'aria2c', # استخدام aria2c لتسريع التحميل
        'external_downloader_args': ['-x', '16', '-s', '16', '-k', '1M'], # 16 اتصال متوازي لأقصى سرعة
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Connection': 'keep-alive',
        }
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        filename = ydl.prepare_filename(info)
        return filename, info.get('title', 'Video')

# دالة ضغط الفيديو إلى أصغر حجم مع الحفاظ على الجودة باستخدام FFmpeg
async def compress_video(input_path, output_path):
    # استخدام كود معيارى CRF 28 لتقليل الحجم بنسبة كبيرة والحفاظ على الجودة
    cmd = f'ffmpeg -y -i "{input_path}" -vcodec libx264 -crf 28 -preset veryfast -acodec aac -b:a 128k "{output_path}"'
    process = await asyncio.create_subprocess_shell(
        cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    await process.communicate()
    return process.returncode == 0

@app.on_message(filters.command("start"))
async def start(_, message: Message):
    await message.reply_text(
        "👋 أهلاً بك في بوت Family House Advanced Leech Bot المطور!\n\n"
        "🚀 تم تفعيل ميزة التحميل فائق السرعة (Multi-Connection) ودعم كافة المواقع العربية (عرب سيد، سيما ناو، ماي سيما، إيجيبست، يوتيوب، إلخ).\n"
        "📉 يتم الآن ضغط مساحة الفيديوهات تلقائياً لأصغر حجم ممكن قبل الرفع لحفظ باقات المتابعين مع الحفاظ الكامل على الجودة.\n\n"
        "أرسل الرابط مباشرة أو استخدم أمر /leech [الرابط] للبدء."
    )

@app.on_message(filters.command("leech") | filters.regex(r'https?://[^\s]+'))
async def leech_handler(client: Client, message: Message):
    if message.from_user.id != OWNER_ID:
        await message.reply_text("❌ عذراً، هذا البوت مخصص للاستخدام الخاص بالمالك فقط.")
        return

    url = message.text
    if message.command and len(message.command) > 1:
        url = message.command[1]
    elif message.command:
        await message.reply_text("❌ يرجى إرسال الرابط بعد الأمر، مثال:\n`/leech https://arabseed.com/...`")
        return

    status_message = await message.reply_text("⚡ جاري سحب الرابط وبدء التحميل الصاروخي عبر خوادم متصلة متعددة... يرجى الانتظار.")

    try:
        # 1. التحميل السريع
        loop = asyncio.get_event_loop()
        file_path, video_title = await loop.run_in_executor(None, download_video, url)
        
        if not os.path.exists(file_path):
            raise Exception("فشل تحميل الملف من الموقع المذكور، يرجى التأكد من مباشرية الرابط.")

        orig_size = os.path.getsize(file_path) / (1024 * 1024)

        await status_message.edit_text(f"📥 اكتمل التحميل السريع (الحجم الأصلي: {orig_size:.1f} MB)\n\n⚙️ جاري الآن تشغيل وحدة الضغط الذكي لتصغير حجم الفيديو وحفظ الجودة...")

        # 2. الضغط الذكي
        compressed_path = os.path.splitext(file_path)[0] + "_compressed.mp4"
        compression_success = await compress_video(file_path, compressed_path)

        if compression_success and os.path.exists(compressed_path):
            final_file = compressed_path
            new_size = os.path.getsize(compressed_path) / (1024 * 1024)
            size_saved = ((orig_size - new_size) / orig_size) * 100
            caption_text = f"🎬 **{video_title}**\n\n📉 تم ضغط المساحة بنسبة: {size_saved:.1f}%\n📦 الحجم النهائي: {new_size:.1f} MB\n\n🔺 حقوق: {WATERMARK_TEXT}"
        else:
            final_file = file_path
            caption_text = f"🎬 **{video_title}**\n\n⚠️ (تعذر الضغط، تم الرفع بالحجم الأصلي)\n📦 الحجم: {orig_size:.1f} MB\n\n🔺 حقوق: {WATERMARK_TEXT}"

        await status_message.edit_text("📤 اكتملت عملية الضغط بنجاح! جاري الآن الرفع الفوري إلى قناتك...")

        # 3. الرفع إلى تليجرام
        await client.send_video(
            chat_id=UPLOAD_CHANNEL,
            video=final_file,
            caption=caption_text,
            supports_streaming=True
        )

        await status_message.edit_text("✅ تم التحميل، الضغط، والرفع بنجاح لجروب/قناة عائلة Family House!")

        # تنظيف السيرفر وحذف الملفات المؤقتة
        if os.path.exists(file_path): os.remove(file_path)
        if os.path.exists(compressed_path): os.remove(compressed_path)

    except Exception as e:
        await status_message.edit_text(f"❌ حدث خطأ أثناء المعالجة:\n`{str(e)}`")
        if 'file_path' in locals() and os.path.exists(file_path): os.remove(file_path)
        if 'compressed_path' in locals() and os.path.exists(compressed_path): os.remove(compressed_path)

if not os.path.exists("downloads"):
    os.makedirs("downloads")

print("⚡ Family House Leech Bot is fully optimized and running...")
app.run()
