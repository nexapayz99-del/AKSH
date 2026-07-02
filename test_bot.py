# test_bot.py
import os
import asyncio
from pyrogram import Client
from dotenv import load_dotenv

load_dotenv()

API_ID = int(os.getenv("API_ID", 0))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")

async def test_bot():
    print("🔍 Testing bot connection...")
    print(f"API_ID: {API_ID}")
    print(f"BOT_TOKEN: {BOT_TOKEN[:10]}...")
    
    try:
        app = Client(
            "test_bot",
            api_id=API_ID,
            api_hash=API_HASH,
            bot_token=BOT_TOKEN
        )
        
        await app.start()
        me = await app.get_me()
        print(f"✅ Bot is working!")
        print(f"📱 Bot username: @{me.username}")
        print(f"🆔 Bot ID: {me.id}")
        await app.stop()
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    asyncio.run(test_bot())
