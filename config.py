import os

# بياناتك الثابتة المدخلة
API_ID = 21621261
API_HASH = "996b2562bb570e9f1e22ccb60726768c"
OWNER_ID = 7030252495

# متغيرات البيئة من لوحة تحكم Railway
BOT_TOKEN = os.environ.get("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
WATERMARK_TEXT = os.environ.get("WATERMARK_TEXT", "Family House")
UPLOAD_CHANNEL = int(os.environ.get("UPLOAD_CHANNEL", -1001234567890))
