import os
import asyncio
import logging
from pyrogram import Client, filters
from pyrogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# --- LOGGING SETUP ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- CONFIGURATION ---
API_ID = int(os.getenv("API_ID", 0))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID", 0))

logger.info(f"API_ID: {API_ID}")
logger.info(f"BOT_TOKEN: {BOT_TOKEN[:10]}...")

# Initialize bot
app = Client(
    "report_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    workdir="./sessions"
)

# --- SIMPLE MENU ---
def get_menu():
    buttons = [
        [KeyboardButton("🚀 Start Reporting")],
        [KeyboardButton("📊 Stats")],
        [KeyboardButton("🛑 Stop Reporting")]
    ]
    return ReplyKeyboardMarkup(buttons, resize_keyboard=True)

# --- COMMAND HANDLERS ---

# 1. /start command - SIMPLE AND TESTED
@app.on_message(filters.command("start") & filters.private)
async def start_command(client, message: Message):
    """Handle /start command"""
    try:
        user_id = message.from_user.id
        logger.info(f"✅ /start received from user: {user_id}")
        
        await message.reply(
            f"✅ **Bot is Working!**\n\n"
            f"Hello {message.from_user.first_name}!\n"
            f"Your ID: `{user_id}`\n\n"
            f"Use the buttons below or send /help",
            reply_markup=get_menu()
        )
    except Exception as e:
        logger.error(f"Error in start: {e}")
        await message.reply(f"❌ Error: {str(e)}")

# 2. /help command
@app.on_message(filters.command("help") & filters.private)
async def help_command(client, message: Message):
    """Handle /help command"""
    logger.info(f"✅ /help received from user: {message.from_user.id}")
    
    await message.reply(
        "📚 **Available Commands:**\n\n"
        "/start - Start the bot\n"
        "/help - Show this help\n"
        "/ping - Check if bot is alive\n"
        "/stats - View your stats\n\n"
        "Or use the buttons below!",
        reply_markup=get_menu()
    )

# 3. /ping command - For testing
@app.on_message(filters.command("ping") & filters.private)
async def ping_command(client, message: Message):
    """Handle /ping command"""
    logger.info(f"✅ /ping received from user: {message.from_user.id}")
    await message.reply("🏓 **Pong!** Bot is alive and working!")

# 4. Handle button clicks and text messages
@app.on_message(filters.text & filters.private)
async def handle_text(client, message: Message):
    """Handle text messages (buttons)"""
    try:
        text = message.text
        user_id = message.from_user.id
        logger.info(f"📨 Text from {user_id}: {text}")
        
        if text == "🚀 Start Reporting":
            await message.reply("🚀 Reporting feature will be added soon!")
        
        elif text == "📊 Stats":
            await message.reply(
                f"📊 **Your Stats:**\n\n"
                f"User ID: `{user_id}`\n"
                f"Reports: 0\n"
                f"Credits: 0"
            )
        
        elif text == "🛑 Stop Reporting":
            await message.reply("🛑 No active reporting tasks.")
        
        else:
            # Echo back any other message
            await message.reply(f"You said: {text}")
            
    except Exception as e:
        logger.error(f"Error in text handler: {e}")
        await message.reply(f"❌ Error: {str(e)}")

# --- MAIN ---
async def main():
    try:
        # Create sessions directory
        os.makedirs("./sessions", exist_ok=True)
        
        logger.info("🤖 Starting bot...")
        
        # Start the bot
        await app.start()
        
        # Get bot info
        me = await app.get_me()
        logger.info(f"✅ Bot started successfully!")
        logger.info(f"📱 Bot username: @{me.username}")
        logger.info(f"🆔 Bot ID: {me.id}")
        logger.info("📍 Bot is running. Press Ctrl+C to stop.")
        
        # Keep the bot running
        await asyncio.Event().wait()
        
    except Exception as e:
        logger.error(f"❌ Error in main: {e}")
        raise
    finally:
        await app.stop()
        logger.info("Bot stopped")

if __name__ == "__main__":
    asyncio.run(main())