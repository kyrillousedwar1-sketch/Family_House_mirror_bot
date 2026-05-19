from pyrogram import Client, filters
from config import *

app = Client(
    "FamilyHouseBot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

@app.on_message(filters.command("start"))
async def start(_, message):
    await message.reply_text("Family House Professional Leech Bot")

@app.on_message(filters.command("leech"))
async def leech(_, message):
    await message.reply_text("Download system ready.")

app.run()
