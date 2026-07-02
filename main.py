# main.py
import os
import asyncio
import logging
from datetime import datetime
from pyrogram import Client, filters
from pyrogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
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

logger.info(f"🤖 Starting bot...")
logger.info(f"API_ID: {API_ID}")
logger.info(f"BOT_TOKEN: {BOT_TOKEN[:10] if BOT_TOKEN else 'NOT SET'}...")

# --- INITIALIZE BOT ---
app = Client(
    "report_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    workdir="./sessions"
)

# --- MENUS ---
def get_main_menu():
    buttons = [
        [KeyboardButton("🚀 Start Reporting")],
        [KeyboardButton("🎯 DM Attack"), KeyboardButton("🤖 Report Bot")],
        [KeyboardButton("📊 Stats"), KeyboardButton("🛑 Stop Reporting")],
        [KeyboardButton("👨‍💻 Contact Admin")]
    ]
    return ReplyKeyboardMarkup(buttons, resize_keyboard=True)

def get_report_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🤖 Spam", callback_data="r_spam"), 
         InlineKeyboardButton("💳 Scam", callback_data="r_scam")],
        [InlineKeyboardButton("🧒 Child Abuse", callback_data="r_child"), 
         InlineKeyboardButton("👊 Violence", callback_data="r_violence")],
        [InlineKeyboardButton("🔞 Adult Content", callback_data="r_porn"), 
         InlineKeyboardButton("⚠️ Other", callback_data="r_other")]
    ])

# --- COMMAND HANDLERS ---

@app.on_message(filters.command("start") & filters.private)
async def start_command(client, message: Message):
    """Handle /start command"""
    try:
        user_id = message.from_user.id
        logger.info(f"✅ /start received from user: {user_id}")
        
        await message.reply(
            f"✅ **Bot Activated!**\n\n"
            f"👋 Hello {message.from_user.first_name}!\n"
            f"🆔 Your ID: `{user_id}`\n\n"
            f"🔹 Use the buttons below to get started.\n"
            f"🔹 Send /help for all commands.",
            reply_markup=get_main_menu()
        )
    except Exception as e:
        logger.error(f"Error in start: {e}")
        await message.reply(f"❌ Error: {str(e)}")

@app.on_message(filters.command("help") & filters.private)
async def help_command(client, message: Message):
    """Handle /help command"""
    try:
        user_id = message.from_user.id
        logger.info(f"✅ /help received from user: {user_id}")
        
        help_text = """
📚 **Available Commands**

**Basic Commands:**
/start - Start the bot
/help - Show this help
/ping - Check if bot is alive
/stats - View your statistics

**Reporting:**
🚀 Start Reporting - Report channels/groups
🎯 DM Attack - Report user profiles  
🤖 Report Bot - Report Telegram bots
🛑 Stop Reporting - Stop active task

**Support:**
👨‍💻 Contact Admin - Message support team

**Admin Commands:**
(Only for authorized admins)
/addaccount - Add Telegram account
/broadcast - Send broadcast message
"""
        await message.reply(help_text, parse_mode='Markdown')
    except Exception as e:
        logger.error(f"Error in help: {e}")
        await message.reply(f"❌ Error: {str(e)}")

@app.on_message(filters.command("ping") & filters.private)
async def ping_command(client, message: Message):
    """Handle /ping command"""
    try:
        user_id = message.from_user.id
        logger.info(f"✅ /ping received from user: {user_id}")
        
        start_time = datetime.now()
        await message.reply("🏓 Pong! Checking bot status...")
        
        # Get bot info
        me = await client.get_me()
        end_time = datetime.now()
        response_time = (end_time - start_time).total_seconds()
        
        await message.reply(
            f"✅ **Bot Status:**\n\n"
            f"📱 Bot: @{me.username}\n"
            f"🆔 ID: {me.id}\n"
            f"⏱️ Response time: {response_time:.2f}s\n"
            f"🔹 Status: Online ✅"
        )
    except Exception as e:
        logger.error(f"Error in ping: {e}")
        await message.reply(f"❌ Error: {str(e)}")

@app.on_message(filters.command("stats") & filters.private)
async def stats_command(client, message: Message):
    """Handle /stats command"""
    try:
        user_id = message.from_user.id
        logger.info(f"✅ /stats received from user: {user_id}")
        
        # Get bot info
        me = await client.get_me()
        
        await message.reply(
            f"📊 **Your Statistics**\n\n"
            f"👤 User ID: `{user_id}`\n"
            f"📱 Bot: @{me.username}\n"
            f"📊 Reports: 0\n"
            f"💳 Credits: 0\n"
            f"📅 Joined: Today"
        )
    except Exception as e:
        logger.error(f"Error in stats: {e}")
        await message.reply(f"❌ Error: {str(e)}")

# --- TEXT MESSAGE HANDLER ---
@app.on_message(filters.text & filters.private)
async def handle_text(client, message: Message):
    """Handle text messages (buttons)"""
    try:
        text = message.text
        user_id = message.from_user.id
        logger.info(f"📨 Text from {user_id}: {text}")
        
        # --- Main Menu Buttons ---
        if text == "🚀 Start Reporting":
            await message.reply(
                "Select report reason:",
                reply_markup=get_report_menu()
            )
        
        elif text == "🎯 DM Attack":
            await message.reply(
                "🎯 **DM Attack Mode**\n\n"
                "Send the @username or user ID of the target.\n"
                "Example: @username or 123456789"
            )
        
        elif text == "🤖 Report Bot":
            await message.reply(
                "🤖 **Report Bot Mode**\n\n"
                "Send the @username of the bot to report.\n"
                "Example: @spam_bot"
            )
        
        elif text == "📊 Stats":
            await stats_command(client, message)
        
        elif text == "🛑 Stop Reporting":
            await message.reply("🛑 No active reporting tasks found.")
        
        elif text == "👨‍💻 Contact Admin":
            if OWNER_ID:
                await message.reply(
                    f"👨‍💻 **Contact Support**\n\n"
                    f"Click below to message the owner:\n"
                    f"🔹 [Message Owner](tg://user?id={OWNER_ID})",
                    disable_web_page_preview=True
                )
            else:
                await message.reply("👨‍💻 No admin configured yet.")
        
        else:
            # Handle target input for reporting
            await message.reply(
                f"⚠️ **Not Implemented Yet**\n\n"
                f"This feature is coming soon!\n"
                f"You sent: `{text}`"
            )
            
    except Exception as e:
        logger.error(f"Error in text handler: {e}")
        await message.reply(f"❌ Error: {str(e)}")

# --- CALLBACK QUERY HANDLER ---
@app.on_callback_query()
async def handle_callback(client, callback_query):
    """Handle inline button clicks"""
    try:
        data = callback_query.data
        user_id = callback_query.from_user.id
        logger.info(f"📨 Callback from {user_id}: {data}")
        
        await callback_query.answer()
        
        if data == "r_spam":
            await callback_query.message.edit_text(
                "🤖 **Spam Report**\n\n"
                "Send the @username, link, or ID of the spam target."
            )
        elif data == "r_scam":
            await callback_query.message.edit_text(
                "💳 **Scam/Fraud Report**\n\n"
                "Send the @username, link, or ID of the scam target."
            )
        elif data == "r_child":
            await callback_query.message.edit_text(
                "🧒 **Child Abuse Report**\n\n"
                "Send the @username, link, or ID of the target."
            )
        elif data == "r_violence":
            await callback_query.message.edit_text(
                "👊 **Violence Report**\n\n"
                "Send the @username, link, or ID of the target."
            )
        elif data == "r_porn":
            await callback_query.message.edit_text(
                "🔞 **Adult Content Report**\n\n"
                "Send the @username, link, or ID of the target."
            )
        elif data == "r_other":
            await callback_query.message.edit_text(
                "⚠️ **Other Report**\n\n"
                "Send the @username, link, or ID of the target.\n"
                "Also include a description of the issue."
            )
        else:
            await callback_query.message.edit_text(
                f"❌ Unknown option: {data}"
            )
            
    except Exception as e:
        logger.error(f"Error in callback: {e}")
        await callback_query.message.reply(f"❌ Error: {str(e)}")

# --- MAIN ---
async def main():
    try:
        # Create sessions directory
        os.makedirs("./sessions", exist_ok=True)
        
        logger.info("🤖 Starting bot...")
        logger.info("📱 Initializing Pyrogram client...")
        
        # Start the bot
        await app.start()
        
        # Get bot info
        me = await app.get_me()
        logger.info(f"✅ Bot started successfully!")
        logger.info(f"📱 Bot username: @{me.username}")
        logger.info(f"🆔 Bot ID: {me.id}")
        logger.info("📍 Bot is running. Press Ctrl+C to stop.")
        
        # Send startup notification to owner
        if OWNER_ID:
            try:
                await app.send_message(
                    OWNER_ID,
                    f"✅ **Bot Started Successfully!**\n\n"
                    f"📱 @{me.username}\n"
                    f"🆔 ID: {me.id}\n"
                    f"⏱️ Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                )
                logger.info(f"📨 Startup notification sent to owner: {OWNER_ID}")
            except Exception as e:
                logger.error(f"Failed to send startup notification: {e}")
        
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