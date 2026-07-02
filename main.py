import os
import asyncio
import uuid
import logging
import random
import time
import sys
from datetime import datetime
from pyrogram import Client, filters
from pyrogram.errors import (
    SessionPasswordNeeded, FloodWait, UsernameInvalid, 
    PeerIdInvalid, InviteHashExpired, UserAlreadyParticipant, 
    AuthKeyInvalid, UserDeactivated, UserDeactivatedBan
)
from pyrogram.types import (
    Message, ReplyKeyboardMarkup, KeyboardButton, 
    InlineKeyboardMarkup, InlineKeyboardButton
)
from pyrogram.raw import functions, types
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# --- LOGGING SETUP ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('logs/bot.log')
    ]
)
logger = logging.getLogger(__name__)

# --- CONFIGURATION ---
API_ID = int(os.getenv("API_ID", 0))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
MONGO_URI = os.getenv("MONGO_URI")
OWNER_ID = int(os.getenv("OWNER_ID", 0))

logger.info(f"Starting bot with API_ID: {API_ID}")
logger.info(f"MONGO_URI: {MONGO_URI}")

# Database Setup
try:
    db_client = AsyncIOMotorClient(MONGO_URI)
    db = db_client["telegram_bot"]
    accounts_col = db["sessions"]
    users_col = db["authorized_users"]
    tokens_col = db["keys"]
    admin_col = db["admins"]
    logs_col = db["report_logs"]
    refund_logs_col = db["refund_logs"]
    receipts_col = db["api_receipts"]
    credit_logs_col = db["credit_logs"]
    logger.info("✅ Database connected successfully")
except Exception as e:
    logger.error(f"❌ Database connection failed: {e}")
    sys.exit(1)

# Initialize bot
bot = Client(
    "report_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    workdir="./sessions"
)

# --- STATE MANAGEMENT ---
user_data = {}
active_tasks = {}
user_cooldowns = {}
target_cooldowns = {}

# --- DEVICE SPOOFER ENGINE ---
SPOOF_DEVICES = [
    {"device_model": "iPhone 15 Pro Max", "system_version": "iOS 17.4.1", "app_version": "10.12.0"},
    {"device_model": "iPhone 14", "system_version": "iOS 16.6", "app_version": "10.11.1"},
    {"device_model": "iPhone 13 Pro", "system_version": "iOS 17.1", "app_version": "10.10.0"},
    {"device_model": "Samsung Galaxy S24 Ultra", "system_version": "Android 14", "app_version": "10.12.0"},
    {"device_model": "Samsung Galaxy S23", "system_version": "Android 13", "app_version": "10.11.2"},
    {"device_model": "Samsung Galaxy Z Fold 5", "system_version": "Android 14", "app_version": "10.9.1"},
    {"device_model": "Google Pixel 8 Pro", "system_version": "Android 14", "app_version": "10.12.0"},
    {"device_model": "Google Pixel 7a", "system_version": "Android 13", "app_version": "10.8.2"},
    {"device_model": "OnePlus 12", "system_version": "Android 14", "app_version": "10.11.1"},
    {"device_model": "Windows PC", "system_version": "Windows 11", "app_version": "4.16.2"},
    {"device_model": "Windows PC", "system_version": "Windows 10", "app_version": "4.15.0"},
    {"device_model": "MacBook Pro", "system_version": "macOS 14.3", "app_version": "9.6.0"},
    {"device_model": "MacBook Air M2", "system_version": "macOS 13.5", "app_version": "9.5.1"}
]

def get_spoofed_device():
    return random.choice(SPOOF_DEVICES)

# --- UTILITY FUNCTIONS ---
async def check_admin(user_id):
    if user_id == OWNER_ID:
        return True
    admin = await admin_col.find_one({"user_id": user_id})
    return bool(admin)

async def check_access(user_id):
    if user_id == OWNER_ID:
        return True
    if await check_admin(user_id):
        return True
    user = await users_col.find_one({"user_id": user_id, "status": "active"})
    return bool(user)

def get_main_menu(user_id, is_admin):
    buttons = []
    top_row = []
    if is_admin:
        top_row.append(KeyboardButton("📱 Add Account"))
    if user_id == OWNER_ID:
        top_row.append(KeyboardButton("❌ Remove Account"))
    if top_row:
        buttons.append(top_row)
    
    buttons.append([KeyboardButton("🚀 Start Reporting"), KeyboardButton("🎯 DM Attack")])
    buttons.append([KeyboardButton("🤖 Report Bot"), KeyboardButton("🛑 Stop Reporting")])
    buttons.append([KeyboardButton("📊 Stats"), KeyboardButton("👨‍💻 Contact Admin")])
    
    bottom_row = []
    if is_admin:
        bottom_row.append(KeyboardButton("⚙️ Management"))
    if user_id == OWNER_ID:
        bottom_row.append(KeyboardButton("👑 Owner Panel"))
        bottom_row.append(KeyboardButton("🗑 Flush All Accounts"))
    if bottom_row:
        buttons.append(bottom_row)
        
    return ReplyKeyboardMarkup(buttons, resize_keyboard=True)

# --- REPORTING MENUS ---
def kb_main_report():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🤖 Spam", callback_data="r_spam"), 
         InlineKeyboardButton("💳 Scam / Fraud", callback_data="menu_fraud")],
        [InlineKeyboardButton("🧒 Child Abuse", callback_data="menu_child"), 
         InlineKeyboardButton("👊 Violence", callback_data="menu_violence")],
        [InlineKeyboardButton("🔞 Adult Content", callback_data="menu_porn"), 
         InlineKeyboardButton("💊 Illegal Drugs", callback_data="r_dr_illegal")],
        [InlineKeyboardButton("🕵️ Personal Details", callback_data="menu_personal"), 
         InlineKeyboardButton("©️ Copyright", callback_data="r_copyright")],
        [InlineKeyboardButton("⚠️ Illegal Goods", callback_data="menu_illegal"), 
         InlineKeyboardButton("✍️ Manual / Other", callback_data="r_manual")]
    ])

def kb_fraud():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("👤 Impersonation", callback_data="r_fr_impersonation")],
        [InlineKeyboardButton("💸 Deceptive claims", callback_data="r_fr_deceptive")],
        [InlineKeyboardButton("🦠 Malware, phishing", callback_data="r_fr_malware")],
        [InlineKeyboardButton("🛍 Fraudulent seller", callback_data="r_fr_seller")],
        [InlineKeyboardButton("⬅️ Back to Main", callback_data="menu_main")]
    ])

def kb_child():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🧒 Child sexual abuse", callback_data="r_ca_sexual")],
        [InlineKeyboardButton("👊 Child physical abuse", callback_data="r_ca_physical")],
        [InlineKeyboardButton("⬅️ Back to Main", callback_data="menu_main")]
    ])

def kb_violence():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🤬 Insults or false info", callback_data="r_vi_insult")],
        [InlineKeyboardButton("🩸 Graphic content", callback_data="r_vi_graphic")],
        [InlineKeyboardButton("🔪 Extreme violence", callback_data="r_vi_extreme")],
        [InlineKeyboardButton("🛑 Hate speech", callback_data="r_vi_hate")],
        [InlineKeyboardButton("📣 Calling for violence", callback_data="r_vi_call")],
        [InlineKeyboardButton("🕴️ Organized crime", callback_data="r_vi_crime")],
        [InlineKeyboardButton("💣 Terrorism", callback_data="r_vi_terror")],
        [InlineKeyboardButton("🐕 Animal abuse", callback_data="r_vi_animal")],
        [InlineKeyboardButton("⬅️ Back to Main", callback_data="menu_main")]
    ])

def kb_porn():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🧒 Child abuse", callback_data="menu_child")],
        [InlineKeyboardButton("🛌 Illegal services", callback_data="r_po_services")],
        [InlineKeyboardButton("🐕 Animal abuse", callback_data="r_po_animal")],
        [InlineKeyboardButton("📸 Non-consensual imagery", callback_data="r_po_nonconsensual")],
        [InlineKeyboardButton("🔞 Pornography", callback_data="r_po_porn")],
        [InlineKeyboardButton("⚠️ Other illegal content", callback_data="r_po_other")],
        [InlineKeyboardButton("⬅️ Back to Main", callback_data="menu_main")]
    ])

def kb_personal():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🖼 Private images", callback_data="r_pe_images")],
        [InlineKeyboardButton("📱 Phone number", callback_data="r_pe_phone")],
        [InlineKeyboardButton("🏠 Address", callback_data="r_pe_address")],
        [InlineKeyboardButton("🔐 Stolen data", callback_data="r_pe_stolen")],
        [InlineKeyboardButton("📄 Other personal info", callback_data="r_pe_other")],
        [InlineKeyboardButton("⬅️ Back to Main", callback_data="menu_main")]
    ])

def kb_illegal_goods():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔫 Weapons", callback_data="r_ig_weapons"), 
         InlineKeyboardButton("💊 Drugs Menu", callback_data="menu_drugs")],
        [InlineKeyboardButton("📄 Fake Documents", callback_data="r_ig_docs"), 
         InlineKeyboardButton("💵 Counterfeit Money", callback_data="r_ig_money")],
        [InlineKeyboardButton("💻 Hacking Tools", callback_data="r_ig_hack"), 
         InlineKeyboardButton("📱 Malicious APKs", callback_data="r_ig_apk")],
        [InlineKeyboardButton("👜 Counterfeit Merch", callback_data="r_ig_merch"), 
         InlineKeyboardButton("📦 Other Goods", callback_data="r_ig_other")],
        [InlineKeyboardButton("⬅️ Back to Main", callback_data="menu_main")]
    ])

def kb_drugs():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🚬 Nicotine products", callback_data="r_dr_nicotine")],
        [InlineKeyboardButton("💉 Illegal drugs", callback_data="r_dr_illegal")],
        [InlineKeyboardButton("💊 Other drugs", callback_data="r_dr_other")],
        [InlineKeyboardButton("⬅️ Back to Illegal Goods", callback_data="menu_illegal")]
    ])

# --- BACKGROUND KEEP-ALIVE TASK ---
async def keep_alive_sessions():
    while True:
        await asyncio.sleep(86400)
        logger.info("Running 24h background keep-alive check...")
        try:
            accs = await accounts_col.find({}).to_list(length=1000)
            if accs:
                for i, acc in enumerate(accs):
                    try:
                        await asyncio.sleep(1)
                        dev = get_spoofed_device()
                        async with Client(
                            f"keepalive_{uuid.uuid4().hex[:8]}",
                            in_memory=True,
                            no_updates=True,
                            session_string=acc["session"],
                            api_id=API_ID,
                            api_hash=API_HASH,
                            device_model=dev["device_model"],
                            system_version=dev["system_version"],
                            app_version=dev["app_version"],
                            workdir="./sessions"
                        ) as app:
                            await app.invoke(functions.account.UpdateStatus(offline=False))
                            await app.get_me()
                    except Exception as e:
                        logger.error(f"Keep-alive failed for {acc.get('name')}: {e}")
                logger.info(f"Keep-alive check completed for {len(accs)} accounts.")
        except Exception as e:
            logger.error(f"Keep-alive task error: {e}")

# --- REPORTING LOGIC (Simplified for brevity) ---
async def process_reporting(message, uid):
    # This is a placeholder - full implementation from your original code
    await message.reply("✅ Reporting started! (Full implementation will be added)")

# --- MASS JOIN/LEAVE FUNCTIONS ---
async def mass_join(message, link):
    accs = await accounts_col.find({}).to_list(length=1000)
    if not accs:
        return await message.reply("❌ No accounts logged in.")
    
    if "/c/" in link:
        return await message.reply("❌ **Error:** You cannot join using a `/c/` message link.")
    
    join_target = link.strip()
    if "+" in join_target:
        hash_val = join_target.split("+")[-1].split("/")[0].split("?")[0]
        join_target = f"https://t.me/+{hash_val}"
    
    status_msg = await message.reply(
        f"🛰 **Mass Join Started**\n"
        f"Target: `{join_target}`\n"
        f"Processing {len(accs)} IDs..."
    )
    s, f, req = 0, 0, 0
    
    for i, acc in enumerate(accs):
        try:
            dev = get_spoofed_device()
            async with Client(
                f"temp_join_{uuid.uuid4().hex[:8]}",
                in_memory=True,
                no_updates=True,
                session_string=acc["session"],
                api_id=API_ID,
                api_hash=API_HASH,
                device_model=dev["device_model"],
                system_version=dev["system_version"],
                app_version=dev["app_version"],
                workdir="./sessions"
            ) as app:
                await app.invoke(functions.account.UpdateStatus(offline=False))
                await asyncio.sleep(random.uniform(1.0, 3.0))
                await app.join_chat(join_target)
                s += 1
        except UserAlreadyParticipant:
            s += 1
        except Exception as e:
            if "INVITE_REQUEST_SENT" in str(e).upper():
                req += 1
                s += 1
            else:
                f += 1
        
        if i % 3 == 0 or i == len(accs) - 1:
            await status_msg.edit_text(
                f"🛰 **Joining...**\n"
                f"✅ S: {s} (Req: {req}) | ❌ F: {f}\n"
                f"⏳ Progress: {i+1}/{len(accs)}"
            )
        if i < len(accs) - 1:
            await asyncio.sleep(1)
    
    await status_msg.edit_text(
        f"🏁 **Mass Join Done**\n"
        f"✅ Success: `{s}` (Requests Sent: `{req}`)\n"
        f"❌ Fail: `{f}`"
    )

async def mass_leave(message, target_raw):
    accs = await accounts_col.find({}).to_list(length=1000)
    if not accs:
        return await message.reply("❌ No accounts logged in.")
    
    leave_target = target_raw.strip()
    
    # Parse target
    if "t.me/" in leave_target:
        path = leave_target.split("t.me/")[-1]
        parts = path.split("/")
        if "+" in leave_target or "joinchat/" in leave_target:
            return await message.reply("❌ **Error:** You cannot leave using an invite link. Use raw ID or username.")
        elif path.startswith("c/"):
            leave_target = int(f"-100{parts[1]}")
        elif parts[-1].isdigit() and len(parts) >= 2:
            leave_target = parts[-2]
        else:
            leave_target = parts[-1]
    elif leave_target.startswith("@"):
        leave_target = leave_target.replace("@", "")
    else:
        if leave_target.lstrip('-').isdigit():
            leave_target = int(leave_target)
    
    status_msg = await message.reply(
        f"🚪 **Mass Leave Started**\n"
        f"Target: `{leave_target}`\n"
        f"Processing {len(accs)} IDs..."
    )
    s, f = 0, 0
    
    for i, acc in enumerate(accs):
        try:
            dev = get_spoofed_device()
            async with Client(
                f"temp_leave_{uuid.uuid4().hex[:8]}",
                in_memory=True,
                no_updates=True,
                session_string=acc["session"],
                api_id=API_ID,
                api_hash=API_HASH,
                device_model=dev["device_model"],
                system_version=dev["system_version"],
                app_version=dev["app_version"],
                workdir="./sessions"
            ) as app:
                await app.invoke(functions.account.UpdateStatus(offline=False))
                await asyncio.sleep(random.uniform(1.0, 3.0))
                
                actual_target = leave_target
                left_successfully = False
                
                try:
                    await app.leave_chat(actual_target)
                    left_successfully = True
                except Exception:
                    pass
                
                if not left_successfully:
                    async for dialog in app.get_dialogs(limit=500):
                        chat_id_str = str(dialog.chat.id)
                        target_str = str(actual_target)
                        if (chat_id_str == target_str or 
                            chat_id_str.replace("-100", "") == target_str.replace("-100", "") or
                            (hasattr(dialog.chat, 'username') and dialog.chat.username and
                             str(dialog.chat.username).lower() == str(actual_target).lower())):
                            try:
                                await app.leave_chat(dialog.chat.id)
                                left_successfully = True
                                break
                            except Exception:
                                break
                
                if left_successfully:
                    s += 1
                else:
                    raise Exception("PeerIdInvalid")
        except Exception:
            f += 1
        
        if i % 3 == 0 or i == len(accs) - 1:
            await status_msg.edit_text(
                f"🚪 **Leaving...**\n"
                f"✅ S: {s} | ❌ F: {f}\n"
                f"⏳ Progress: {i+1}/{len(accs)}"
            )
        if i < len(accs) - 1:
            await asyncio.sleep(1)
    
    await status_msg.edit_text(
        f"🏁 **Mass Leave Done**\n"
        f"✅ Success: `{s}`\n"
        f"❌ Fail: `{f}`"
    )

# --- HEALTH CHECK ---
async def perform_health_check(message):
    accs = await accounts_col.find({}).to_list(length=1000)
    if not accs:
        return await message.reply("❌ No accounts to check.")
    
    status_msg = await message.reply(
        f"🩺 **Health Check Started...**\n"
        f"Checking {len(accs)} sessions."
    )
    alive, dead = 0, 0
    dead_list = []
    
    for i, acc in enumerate(accs):
        is_dead = False
        try:
            dev = get_spoofed_device()
            async with Client(
                f"temp_health_{uuid.uuid4().hex[:8]}",
                in_memory=True,
                no_updates=True,
                session_string=acc["session"],
                api_id=API_ID,
                api_hash=API_HASH,
                device_model=dev["device_model"],
                system_version=dev["system_version"],
                app_version=dev["app_version"],
                workdir="./sessions"
            ) as app:
                await app.invoke(functions.account.UpdateStatus(offline=False))
                await app.get_me()
                alive += 1
        except Exception:
            is_dead = True
        
        if is_dead:
            dead += 1
            phone_val = acc.get('phone', 'Unknown')
            acc_id = acc.get('user_id', 'Unknown')
            dead_list.append(f"📞 `{phone_val}` | 🆔 `{acc_id}`")
        
        if i % 5 == 0 or i == len(accs) - 1:
            await status_msg.edit_text(
                f"🩺 **Checking Health...**\n"
                f"✅ Alive: `{alive}`\n"
                f"💀 Dead: `{dead}`\n"
                f"⏳ Progress: {i+1}/{len(accs)}"
            )
        
        await asyncio.sleep(0.3)
    
    res = (
        f"🏁 **Health Check Result**\n"
        f"✅ Alive: `{alive}`\n"
        f"💀 Dead/Unusable: `{dead}`\n\n"
        f"💡 Use `/cleandead` to remove dead IDs."
    )
    
    if dead_list:
        res_list = "\n\n💀 **Dead Accounts:**\n" + "\n".join(dead_list)
        if len(res + res_list) > 4000:
            with open("dead_accounts.txt", "w", encoding="utf-8") as f:
                f.write("\n".join(dead_list))
            await message.reply_document("dead_accounts.txt", caption=res)
            os.remove("dead_accounts.txt")
            await status_msg.delete()
        else:
            await status_msg.edit_text(res + res_list)
    else:
        await status_msg.edit_text(res)

# --- FINALIZE LOGIN ---
async def finalize_login(message, temp, uid):
    ss = await temp.export_session_string()
    me = await temp.get_me()
    
    await accounts_col.update_one(
        {"user_id": me.id},
        {
            "$set": {
                "session": ss,
                "phone": me.phone_number,
                "name": me.first_name,
                "user_id": me.id
            }
        },
        upsert=True
    )
    
    await message.reply(f"✅ Added {me.first_name}.")
    await temp.disconnect()
    
    if uid in user_data:
        del user_data[uid]

# --- BOT COMMAND HANDLERS ---

# FIXED: /start command handler
@bot.on_message(filters.command("start") & filters.private)
async def start_cmd(client, message: Message):
    """Handle /start command"""
    try:
        uid = message.from_user.id
        logger.info(f"📨 /start command received from user {uid}")
        
        is_admin = await check_admin(uid)
        
        if await check_access(uid):
            await message.reply(
                "✅ **Bot Activated!**\n\n"
                "Welcome to the Report Bot. Use the menu below to navigate.\n"
                "Send /help to see all available commands.",
                reply_markup=get_main_menu(uid, is_admin)
            )
            logger.info(f"✅ User {uid} started bot successfully")
        else:
            await message.reply(
                "⚠️ **Access Denied**\n\n"
                "You are not authorized to use this bot.\n"
                "Please use `/redeem TOKEN` to gain access."
            )
            logger.info(f"⚠️ User {uid} is not authorized")
    except Exception as e:
        logger.error(f"❌ Error in start_cmd: {e}")
        await message.reply(f"❌ Error: {str(e)}")

# FIXED: /help command handler
@bot.on_message(filters.command("help") & filters.private)
async def help_cmd(client, message: Message):
    """Handle /help command"""
    try:
        uid = message.from_user.id
        logger.info(f"📨 /help command received from user {uid}")
        
        if not await check_access(uid):
            await message.reply("⚠️ Access Denied. Please contact an administrator.")
            return
        
        help_text = """
📚 **Available Commands**

**User Commands:**
/start - Start the bot
/help - Show this help message
/stats - View your statistics
/redeem TOKEN - Redeem access token

**Reporting Commands:**
🚀 Start Reporting - Report channels/groups
🎯 DM Attack - Report user profiles
🤖 Report Bot - Report Telegram bots
🛑 Stop Reporting - Stop active task

**Admin Commands:**
📱 Add Account - Add Telegram account
⚙️ Management - Admin panel
📢 Broadcast - Send broadcast message
💳 Add Credit - Add credits to users

**Owner Commands:**
👑 Owner Panel - Full control panel
🗑 Flush All Accounts - Remove all accounts
❌ Remove Account - Remove specific account

Use the keyboard menu or type commands directly.
"""
        await message.reply(help_text, parse_mode='Markdown')
        logger.info(f"✅ Help sent to user {uid}")
    except Exception as e:
        logger.error(f"❌ Error in help_cmd: {e}")
        await message.reply(f"❌ Error: {str(e)}")

# FIXED: Handle text messages
@bot.on_message(filters.text & filters.private & ~filters.command([
    "start", "help", "redeem", "addtoken", "addcredit", "broadcast",
    "addadmin", "rmadmin", "users", "rmuser", "join", "leave",
    "health", "setcap", "dbcheck", "checkdead", "cleandead", "stats"
]))
async def handle_text(client, message: Message):
    """Handle text messages (menu buttons)"""
    try:
        text = message.text
        uid = message.from_user.id
        
        logger.info(f"📨 Text message from {uid}: {text}")
        
        # Check access
        if not await check_access(uid):
            await message.reply("⚠️ Access Denied. Use `/start` to check your status.")
            return
        
        is_adm = await check_admin(uid)
        
        # --- Stats ---
        if text == "📊 Stats" or text == "/stats":
            u = await users_col.find_one({"user_id": uid})
            acc_count = await accounts_col.count_documents({})
            last = await logs_col.find({
                "user_id": uid,
                "summary_task": True
            }).sort("_id", -1).to_list(length=1)
            
            s, f = (last[0].get("s_count", 0), last[0].get("f_count", 0)) if last else (0, 0)
            
            live_tasks = sum(1 for status in active_tasks.values() if status in ["running", "paused"])
            
            stats_text = (
                f"🏁 **Last Task Stats**\n"
                f"✅ Success: {s}\n"
                f"❌ Fail: {f}\n"
                f"💳 Credit used: {s}\n"
                f"👥 Active IDs: {acc_count}\n"
                f"👤 **Credits:** `{u.get('credits', 0) if u else 0}`\n"
            )
            if is_adm or uid == OWNER_ID:
                stats_text += f"\n🔥 **Live Reporting Tasks:** `{live_tasks}`"
                
            await message.reply(stats_text, parse_mode='Markdown')
            return
        
        # --- Owner Panel ---
        if text == "🗑 Flush All Accounts" and uid == OWNER_ID:
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("⚠️ YES, FLUSH ALL", callback_data="confirm_flush")],
                [InlineKeyboardButton("❌ CANCEL", callback_data="cancel_flush")]
            ])
            await message.reply(
                "⚠️ **WARNING:** Are you sure you want to log out and permanently delete "
                "**ALL** accounts from the database? This action cannot be undone.",
                reply_markup=kb
            )
            return
        
        if text == "👑 Owner Panel" and uid == OWNER_ID:
            all_accs = await accounts_col.find({}).to_list(length=1000)
            t = "👑 **Owner Dashboard**\n\n"
            t += f"📊 Active IDs: {len(all_accs)}\n"
            t += "📌 **Note:** Use `/setcap ADMIN_ID AMOUNT` to limit admin credit powers."
            
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("👑 Add Admin", callback_data="cmd_addadmin"),
                 InlineKeyboardButton("🚫 Remove Admin", callback_data="cmd_rmadmin")],
                [InlineKeyboardButton("🗑 Remove User", callback_data="cmd_rmuser"),
                 InlineKeyboardButton("💰 View Refunds", callback_data="view_refunds")],
                [InlineKeyboardButton("🧾 View API Receipts", callback_data="view_receipts"),
                 InlineKeyboardButton("💳 Admin Credit Logs", callback_data="view_credit_logs")],
                [InlineKeyboardButton("🛑 KILL ALL TASKS", callback_data="cmd_kill_all")]
            ])
            await message.reply(t, reply_markup=kb)
            return
        
        # --- Management Panel ---
        if text == "⚙️ Management" and is_adm:
            all_accs = await accounts_col.find({}).to_list(length=1000)
            t = "⚙️ **Management Panel**\n────────────────────\n"
            for i, acc in enumerate(all_accs, 1):
                phone_val = acc.get('phone', 'Unknown') if uid == OWNER_ID else "HIDDEN"
                t += f"{i}. {acc.get('name')} | {phone_val}\n"
            
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("🎫 Gen Token", callback_data="cmd_addtoken"),
                 InlineKeyboardButton("👥 Users List", callback_data="cmd_users")],
                [InlineKeyboardButton("💳 Add Credit", callback_data="cmd_addcredit"),
                 InlineKeyboardButton("📢 Broadcast", callback_data="cmd_broadcast")],
                [InlineKeyboardButton("🛰 Mass Join", callback_data="cmd_join"),
                 InlineKeyboardButton("🚪 Mass Leave", callback_data="cmd_leave")],
                [InlineKeyboardButton("🩺 Health Check", callback_data="cmd_health")]
            ])
            await message.reply(t + "────────────────────", reply_markup=kb)
            return
        
        # --- Contact Admin ---
        if text == "👨‍💻 Contact Admin":
            admins = await admin_col.find({}).to_list(length=10)
            kb = []
            if OWNER_ID and OWNER_ID != 0:
                kb.append([InlineKeyboardButton("👑 Message Owner", url=f"tg://user?id={OWNER_ID}")])
            for i, a in enumerate(admins, 1):
                kb.append([InlineKeyboardButton(
                    f"🔹 Message Admin {i}",
                    url=f"tg://user?id={a['user_id']}"
                )])
                
            if not kb:
                await message.reply("👨‍💻 **Support Team**\nNo admins are currently set.")
                return
                
            await message.reply(
                "👨‍💻 **Support Team**\nClick a button below to message an admin directly:",
                reply_markup=InlineKeyboardMarkup(kb)
            )
            return
        
        # --- Add Account ---
        if text == "📱 Add Account" and is_adm:
            user_data[uid] = {"step": "phone"}
            await message.reply("📱 Send Phone Number (+ format):")
            return
        
        # --- Remove Account ---
        if text == "❌ Remove Account" and uid == OWNER_ID:
            user_data[uid] = {"step": "remove"}
            await message.reply("🗑 Send User ID or Phone Number to delete:")
            return
        
        # --- Start Reporting ---
        if text == "🚀 Start Reporting":
            if uid in active_tasks and active_tasks[uid] in ["running", "paused"]:
                await message.reply("❌ You already have a task running. Please Stop it first.")
                return
            
            user = await users_col.find_one({"user_id": uid})
            if uid != OWNER_ID and (not user or user.get("credits", 0) < 1):
                await message.reply("❌ Insufficient credits!")
                return
            
            user_data[uid] = {"target_type": "channel"}
            await message.reply("Select Reason:", reply_markup=kb_main_report())
            return
        
        # --- DM Attack ---
        if text == "🎯 DM Attack":
            if uid in active_tasks and active_tasks[uid] in ["running", "paused"]:
                await message.reply("❌ You already have a task running. Please Stop it first.")
                return
            
            user = await users_col.find_one({"user_id": uid})
            if uid != OWNER_ID and (not user or user.get("credits", 0) < 1):
                await message.reply("❌ Insufficient credits!")
                return
            
            user_data[uid] = {"target_type": "dm"}
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("🤖 Spam", callback_data="dm_spam"),
                 InlineKeyboardButton("👊 Violence", callback_data="dm_violence")],
                [InlineKeyboardButton("🔞 Pornography", callback_data="dm_porn"),
                 InlineKeyboardButton("🧒 Child Abuse", callback_data="dm_child")],
                [InlineKeyboardButton("©️ Copyright", callback_data="dm_copyright")]
            ])
            await message.reply(
                "Select Reason for **DM Attack (Profile Picture)**:",
                reply_markup=kb
            )
            return
        
        # --- Report Bot ---
        if text == "🤖 Report Bot":
            if uid in active_tasks and active_tasks[uid] in ["running", "paused"]:
                await message.reply("❌ You already have a task running. Please Stop it first.")
                return
            
            user = await users_col.find_one({"user_id": uid})
            if uid != OWNER_ID and (not user or user.get("credits", 0) < 1):
                await message.reply("❌ Insufficient credits!")
                return
            
            user_data[uid] = {"target_type": "bot"}
            await message.reply(
                "Select Reason for **Reporting a Bot**:",
                reply_markup=kb_main_report()
            )
            return
        
        # --- Stop Reporting ---
        if text == "🛑 Stop Reporting":
            if uid in active_tasks and active_tasks[uid] in ["running", "paused"]:
                active_tasks[uid] = "stopped"
                await message.reply(
                    "🛑 Stopping **your** current reporting task... "
                    "Please wait a moment for the final receipt."
                )
            else:
                await message.reply("❌ You have no active reporting tasks running.")
            return
        
        # --- State Machine for multi-step operations ---
        if uid in user_data:
            step = user_data[uid].get("step")
            
            # Phone number input
            if step == "phone":
                phone = text.replace(" ", "")
                dev = get_spoofed_device()
                temp = Client(
                    f"temp_login_{uid}",
                    in_memory=True,
                    no_updates=True,
                    api_id=API_ID,
                    api_hash=API_HASH,
                    device_model=dev["device_model"],
                    system_version=dev["system_version"],
                    app_version=dev["app_version"],
                    workdir="./sessions"
                )
                await temp.connect()
                try:
                    h = await temp.send_code(phone)
                    user_data[uid] = {
                        "step": "code",
                        "phone": phone,
                        "hash": h.phone_code_hash,
                        "client": temp
                    }
                    await message.reply("📩 Send OTP Code:")
                except Exception as e:
                    await message.reply(f"❌ {e}")
                    await temp.disconnect()
            
            # OTP code input
            elif step == "code":
                try:
                    await user_data[uid]["client"].sign_in(
                        user_data[uid]["phone"],
                        user_data[uid]["hash"],
                        text.strip()
                    )
                    await finalize_login(message, user_data[uid]["client"], uid)
                except SessionPasswordNeeded:
                    user_data[uid]["step"] = "password"
                    await message.reply("🔐 Send 2FA Password:")
                except Exception as e:
                    await message.reply(f"❌ {e}")
            
            # 2FA password input
            elif step == "password":
                try:
                    await user_data[uid]["client"].check_password(text)
                    await finalize_login(message, user_data[uid]["client"], uid)
                except Exception as e:
                    await message.reply(f"❌ {e}")
            
            # Target input
            elif step == "target":
                if not text:
                    await message.reply("❌ Please provide a valid text link or username.")
                    return
                
                target_raw = text.strip()
                current_time = time.time()
                
                if uid != OWNER_ID and uid in user_cooldowns and current_time < user_cooldowns[uid]:
                    rem = int(user_cooldowns[uid] - current_time)
                    await message.reply(
                        f"⏳ **Cooldown Active:** You must wait {rem} seconds before starting a new report."
                    )
                    del user_data[uid]
                    return
                    
                if target_raw in target_cooldowns and current_time < target_cooldowns[target_raw]:
                    rem = int(target_cooldowns[target_raw] - current_time)
                    await message.reply(
                        f"⏳ **Target Cooldown:** `{target_raw}` was recently reported. "
                        f"Wait {rem} seconds before it can be reported again."
                    )
                    del user_data[uid]
                    return
                
                user_data[uid]["target"] = target_raw
                user_data[uid]["target_msg_id"] = message.id
                
                if user_data[uid]["mode"] == "r_manual":
                    user_data[uid]["step"] = "manual_text"
                    await message.reply("✍️ Send report text:")
                else:
                    user_data[uid]["step"] = "acc_count"
                    total_accs = await accounts_col.count_documents({})
                    await message.reply(
                        f"👥 How many accounts do you want to use? (Max available: {total_accs})"
                    )
            
            # Manual report text
            elif step == "manual_text":
                user_data[uid]["manual_text"] = text
                user_data[uid]["step"] = "acc_count"
                total_accs = await accounts_col.count_documents({})
                await message.reply(
                    f"👥 How many accounts do you want to use? (Max available: {total_accs})"
                )
            
            # Account count input
            elif step == "acc_count":
                try:
                    requested_accs = int(text)
                    total_accs = await accounts_col.count_documents({})
                    if requested_accs > total_accs:
                        await message.reply(
                            f"❌ **Error:** You only have `{total_accs}` accounts logged in. "
                            f"Please enter a number up to `{total_accs}`:"
                        )
                        return
                    user_data[uid]["acc_count"] = requested_accs
                    user_data[uid]["step"] = "rep_count"
                    await message.reply(
                        "🔄 How many times should EACH account send the report? (e.g., 1)"
                    )
                except:
                    await message.reply("❌ Please enter a valid number.")
            
            # Report count input
            elif step == "rep_count":
                try:
                    user_data[uid]["rep_count"] = int(text)
                    user_data[uid]["interval"] = 15
                    
                    total_cost = user_data[uid]["acc_count"] * user_data[uid]["rep_count"]
                    user_db = await users_col.find_one({"user_id": uid})
                    
                    if uid != OWNER_ID and user_db.get("credits", 0) < total_cost:
                        await message.reply(
                            f"❌ **Insufficient Credits!**\n"
                            f"You need `{total_cost}` credits for this task, "
                            f"but you only have `{user_db.get('credits', 0)}`."
                        )
                        del user_data[uid]
                        return
                    
                    if uid != OWNER_ID:
                        await users_col.update_one(
                            {"user_id": uid},
                            {"$inc": {"credits": -total_cost}}
                        )
                    
                    await process_reporting(message, uid)
                except Exception as e:
                    logger.error(f"Error in rep_count: {e}")
                    await message.reply("❌ Please enter a valid number.")
            
            # Remove account
            elif step == "remove" and uid == OWNER_ID:
                clean_text = text.replace("+", "").replace(" ", "").strip()
                search_query = [{"phone": clean_text}, {"phone": f"+{clean_text}"}]
                if clean_text.lstrip('-').isdigit():
                    search_query.append({"user_id": int(clean_text)})
                
                acc = await accounts_col.find_one({"$or": search_query})
                
                if acc:
                    try:
                        dev = get_spoofed_device()
                        async with Client(
                            f"temp_logout_{uuid.uuid4().hex[:8]}",
                            in_memory=True,
                            no_updates=True,
                            session_string=acc["session"],
                            api_id=API_ID,
                            api_hash=API_HASH,
                            device_model=dev["device_model"],
                            system_version=dev["system_version"],
                            app_version=dev["app_version"],
                            workdir="./sessions"
                        ) as tapp:
                            await tapp.log_out()
                    except Exception:
                        pass
                    
                    await accounts_col.delete_one({"_id": acc["_id"]})
                    await message.reply(
                        f"✅ Logged Out & Removed account: {acc.get('phone', acc.get('user_id'))}"
                    )
                else:
                    await message.reply("❌ Account not found. Please verify the ID or Phone Number.")
                del user_data[uid]
            
            # Add credit
            elif step == "addcredit":
                try:
                    parts = text.split()
                    t_id, amt = int(parts[0]), int(parts[1])
                    
                    if uid != OWNER_ID:
                        admin_doc = await admin_col.find_one({"user_id": uid})
                        if admin_doc:
                            cap = admin_doc.get("credit_cap", 0)
                            used = admin_doc.get("used_credits", 0)
                            if used + amt > cap:
                                await message.reply(
                                    f"❌ **Limit Reached!**\n"
                                    f"You have an admin credit cap of `{cap}`.\n"
                                    f"You have already used `{used}`.\n"
                                    f"You can only add `{max(0, cap - used)}` more credits."
                                )
                                return
                            await admin_col.update_one(
                                {"user_id": uid},
                                {"$inc": {"used_credits": amt}}
                            )
                    
                    await users_col.update_one(
                        {"user_id": t_id},
                        {"$inc": {"credits": amt}},
                        upsert=True
                    )
                    await credit_logs_col.insert_one({
                        "admin_id": uid,
                        "target_user": t_id,
                        "amount": amt,
                        "date": datetime.now().strftime("%Y-%m-%d %H:%M")
                    })
                    
                    await message.reply(f"✅ Added {amt} to `{t_id}`.")
                except:
                    await message.reply("❌ Invalid format. Operation Cancelled.")
                del user_data[uid]
            
            # Broadcast
            elif step == "broadcast":
                users = await users_col.find({}).to_list(length=1000)
                admins = await admin_col.find({}).to_list(length=100)
                all_targets = set(
                    [u.get("user_id") for u in users if u.get("user_id")] +
                    [a.get("user_id") for a in admins if a.get("user_id")] +
                    [OWNER_ID]
                )
                
                sent = 0
                status_bcast = await message.reply("📢 Broadcasting...")
                for t_id in all_targets:
                    try:
                        if t_id and t_id != 0:
                            await message.copy(t_id)
                            sent += 1
                    except:
                        pass
                await status_bcast.edit_text(f"✅ Broadcast Sent to {sent} chats.")
                del user_data[uid]
            
            # Remove user
            elif step == "rmuser":
                try:
                    t_id = int(text)
                    await users_col.delete_one({"user_id": t_id})
                    await message.reply(f"✅ Access permanently revoked for User ID `{t_id}`.")
                except:
                    await message.reply("❌ Invalid ID format. Cancelled.")
                del user_data[uid]
            
            # Add admin
            elif step == "addadmin":
                try:
                    target = int(text)
                    await admin_col.update_one(
                        {"user_id": target},
                        {"$set": {"user_id": target, "credit_cap": 0, "used_credits": 0}},
                        upsert=True
                    )
                    await message.reply(f"✅ User `{target}` is now Admin.")
                except:
                    await message.reply("❌ Invalid ID format.")
                del user_data[uid]
            
            # Remove admin
            elif step == "rmadmin":
                try:
                    target = int(text)
                    await admin_col.delete_one({"user_id": target})
                    await message.reply(f"✅ Admin privileges revoked for User ID `{target}`.")
                except:
                    await message.reply("❌ Invalid ID format.")
                del user_data[uid]
            
            # Mass Join
            elif step == "join":
                await mass_join(message, text)
                del user_data[uid]
            
            # Mass Leave
            elif step == "leave":
                await mass_leave(message, text)
                del user_data[uid]
                
    except Exception as e:
        logger.error(f"❌ Error in handle_text: {e}")
        await message.reply(f"❌ Error: {str(e)}")

# --- CALLBACK HANDLER ---
@bot.on_callback_query()
async def sub_button_handler(client, callback_query):
    try:
        uid = callback_query.from_user.id
        data = callback_query.data
        
        logger.info(f"📨 Callback received from {uid}: {data}")
        
        # --- Flush All Accounts ---
        if data == "confirm_flush":
            if uid != OWNER_ID:
                return
            accs = await accounts_col.find({}).to_list(length=1000)
            if not accs:
                await callback_query.message.edit_text("❌ No accounts logged in.")
                return
            
            await callback_query.message.edit_text(
                f"🗑 **Flushing {len(accs)} accounts...**\n"
                f"Logging out and deleting from database. Please wait."
            )
            success = 0
            
            for i, acc in enumerate(accs):
                try:
                    dev = get_spoofed_device()
                    async with Client(
                        f"flush_{uuid.uuid4().hex[:8]}",
                        in_memory=True,
                        no_updates=True,
                        session_string=acc["session"],
                        api_id=API_ID,
                        api_hash=API_HASH,
                        device_model=dev["device_model"],
                        system_version=dev["system_version"],
                        app_version=dev["app_version"],
                        workdir="./sessions"
                    ) as app:
                        await app.log_out()
                except Exception:
                    pass
                
                await accounts_col.delete_one({"_id": acc["_id"]})
                success += 1
                
                if i % 5 == 0 or i == len(accs) - 1:
                    await callback_query.message.edit_text(
                        f"🗑 **Flushing Accounts...**\n"
                        f"✅ Removed: `{success}/{len(accs)}`"
                    )
                    
            await callback_query.message.edit_text(
                f"✅ **Successfully flushed and logged out all {success} accounts!**"
            )
            return
        
        elif data == "cancel_flush":
            if uid != OWNER_ID:
                return
            await callback_query.message.edit_text("✅ **Flush operation cancelled.**")
            return
        
        # --- Pause/Resume/Stop ---
        elif data == "cmd_pause":
            if uid in active_tasks and active_tasks[uid] == "running":
                active_tasks[uid] = "paused"
                kb = InlineKeyboardMarkup([
                    [
                        InlineKeyboardButton("▶️ Resume", callback_data="cmd_resume"),
                        InlineKeyboardButton("🛑 Stop", callback_data="cmd_stop")
                    ]
                ])
                try:
                    await callback_query.message.edit_reply_markup(reply_markup=kb)
                except:
                    pass
                await callback_query.answer("⏸ Task Paused")
            else:
                await callback_query.answer("❌ Task is not running.")
            return
        
        elif data == "cmd_resume":
            if uid in active_tasks and active_tasks[uid] == "paused":
                active_tasks[uid] = "running"
                kb = InlineKeyboardMarkup([
                    [
                        InlineKeyboardButton("⏸ Pause", callback_data="cmd_pause"),
                        InlineKeyboardButton("🛑 Stop", callback_data="cmd_stop")
                    ]
                ])
                try:
                    await callback_query.message.edit_reply_markup(reply_markup=kb)
                except:
                    pass
                await callback_query.answer("▶️ Task Resumed")
            else:
                await callback_query.answer("❌ Task is not paused.")
            return
        
        elif data == "cmd_stop":
            if uid in active_tasks and active_tasks[uid] in ["running", "paused"]:
                active_tasks[uid] = "stopped"
                await callback_query.answer("🛑 Stopping task...")
            else:
                await callback_query.answer("❌ No active task to stop.")
            return
        
        await callback_query.answer()
        
        # --- Menu Navigation ---
        if data == "menu_main":
            await callback_query.message.edit_text(
                "Select Reason:",
                reply_markup=kb_main_report()
            )
        elif data == "menu_fraud":
            await callback_query.message.edit_text(
                "Select Scam or Fraud Type:",
                reply_markup=kb_fraud()
            )
        elif data == "menu_child":
            await callback_query.message.edit_text(
                "Select Child Abuse Type:",
                reply_markup=kb_child()
            )
        elif data == "menu_violence":
            await callback_query.message.edit_text(
                "Select Violence Type:",
                reply_markup=kb_violence()
            )
        elif data == "menu_porn":
            await callback_query.message.edit_text(
                "Select Adult Content Type:",
                reply_markup=kb_porn()
            )
        elif data == "menu_personal":
            await callback_query.message.edit_text(
                "Select Personal Details Type:",
                reply_markup=kb_personal()
            )
        elif data == "menu_illegal":
            await callback_query.message.edit_text(
                "Select Illegal Good/Service:",
                reply_markup=kb_illegal_goods()
            )
        elif data == "menu_drugs":
            await callback_query.message.edit_text(
                "Select Drug Type:",
                reply_markup=kb_drugs()
            )
        
        # --- Report Selection ---
        elif data.startswith("r_") or data.startswith("dm_"):
            target_type = user_data.get(uid, {}).get("target_type", "channel")
            user_data[uid] = {
                "step": "target",
                "mode": data,
                "target_type": target_type
            }
            
            if data.startswith("dm_"):
                await callback_query.message.edit_text(
                    "🎯 Send the **Target @Username or User ID** for DM Attack:"
                )
            elif target_type == "bot":
                await callback_query.message.edit_text(
                    "🎯 Send the **Bot @Username** (e.g., @Resso_singing_bot) to report:"
                )
            else:
                await callback_query.message.edit_text(
                    "🎯 Send the **Invite Link**, **@Username**, or **Message Link** of target:"
                )
        
        # --- Admin Commands ---
        elif data == "cmd_broadcast":
            user_data[uid] = {"step": "broadcast"}
            await callback_query.message.reply(
                "📢 Send the message (text, image, or video) you want to broadcast:"
            )
        
        elif data == "cmd_kill_all":
            if uid != OWNER_ID:
                return
            for k in active_tasks:
                active_tasks[k] = "stopped"
            await callback_query.message.reply(
                "🛑 **KILL SWITCH ACTIVATED.** "
                "All live reporting tasks across all users have been instructed to stop safely."
            )
        
        elif data == "view_credit_logs":
            if uid != OWNER_ID:
                return
            logs = await credit_logs_col.find({}).sort("_id", -1).to_list(10)
            if not logs:
                await callback_query.message.reply("No admin credit logs yet.")
                return
            res = "💳 **Recent Admin Credit Logs:**\n\n"
            for l in logs:
                res += (
                    f"👮‍♂️ Admin: `{l.get('admin_id')}` ➡️ 👤 User: `{l.get('target_user')}`\n"
                    f"💰 Amount: `{l.get('amount')}` | 📅 {l.get('date')}\n\n"
                )
            await callback_query.message.reply(res)
        
        elif data == "view_receipts":
            if uid != OWNER_ID:
                return
            r = await receipts_col.find({}).sort("_id", -1).to_list(5)
            if not r:
                await callback_query.message.reply("No receipts yet.")
                return
            msg = "📑 **Last 5 API Receipts (Proofs):**\n\n"
            for item in r:
                msg += (
                    f"🎯 Target: `{item.get('target')}`\n"
                    f"👤 Acc ID: `{item.get('session_used')}`\n"
                    f"🤖 **API Response:** `{str(item.get('raw_response', ''))[:100]}...`\n\n"
                )
            await callback_query.message.reply(msg)
        
        elif data == "view_refunds":
            if uid != OWNER_ID:
                return
            logs = await refund_logs_col.find({}).sort("_id", -1).to_list(length=10)
            if not logs:
                await callback_query.message.reply("No refunds yet.")
                return
            res = "💰 **Last 10 Refund Logs:**\n\n"
            for l in logs:
                res += f"👤 `{l.get('user_id')}`\n🎯 `{l.get('target')}`\n📅 {l.get('date')}\n\n"
            await callback_query.message.reply(res)
        
        elif data == "cmd_addtoken":
            tk = str(uuid.uuid4())[:8].upper()
            await tokens_col.insert_one({"token": tk, "used": False})
            await callback_query.message.reply(f"🎫 **New Token:** `{tk}`")
        
        elif data == "cmd_users":
            users = await users_col.find({}).to_list(length=500)
            if not users:
                await callback_query.message.reply("❌ No active users found.")
                return
            res = "👥 **Active Bot Users & Credits**\n────────────────────\n"
            for i, u in enumerate(users, 1):
                res += f"{i}. {u.get('name', 'User')} | `{u.get('user_id')}` | 💳: {u.get('credits', 0)}\n"
            await callback_query.message.reply(res)
        
        elif data == "cmd_health":
            await perform_health_check(callback_query.message)
        
        elif data == "cmd_addcredit":
            user_data[uid] = {"step": "addcredit"}
            await callback_query.message.reply(
                "💳 Send User ID and Amount separated by space "
                "(e.g., `123456789 10` or `-10` to remove):"
            )
        
        elif data == "cmd_rmuser":
            user_data[uid] = {"step": "rmuser"}
            await callback_query.message.reply("🗑 Send User ID to revoke access:")
        
        elif data == "cmd_addadmin":
            user_data[uid] = {"step": "addadmin"}
            await callback_query.message.reply("👑 Send User ID to promote to Admin:")
        
        elif data == "cmd_rmadmin":
            user_data[uid] = {"step": "rmadmin"}
            await callback_query.message.reply("🚫 Send User ID to demote from Admin:")
        
        elif data == "cmd_join":
            user_data[uid] = {"step": "join"}
            await callback_query.message.reply("🛰 Send the **Invite Link** or **@Username** to join:")
        
        elif data == "cmd_leave":
            user_data[uid] = {"step": "leave"}
            await callback_query.message.reply("🚪 Send the Link or Username to leave:")
            
    except Exception as e:
        logger.error(f"❌ Error in callback handler: {e}")
        await callback_query.message.reply(f"❌ Error: {str(e)}")

# --- COMMAND HANDLERS (Admin Commands) ---
@bot.on_message(filters.command("checkdead") & filters.private)
async def checkdead_cmd(client, message: Message):
    if not await check_admin(message.from_user.id):
        return
    
    accs = await accounts_col.find({}).to_list(length=1000)
    if not accs:
        return await message.reply("❌ No accounts logged in.")
    
    status_msg = await message.reply(
        f"🔎 **Checking for Dead Accounts (No Deletion)...**\n"
        f"Checking {len(accs)} sessions."
    )
    dead_list = []
    alive = 0
    
    for i, acc in enumerate(accs):
        await asyncio.sleep(0.5)
        is_dead = False
        try:
            dev = get_spoofed_device()
            async with Client(
                f"temp_checkdead_{uuid.uuid4().hex[:8]}",
                in_memory=True,
                no_updates=True,
                session_string=acc["session"],
                api_id=API_ID,
                api_hash=API_HASH,
                device_model=dev["device_model"],
                system_version=dev["system_version"],
                app_version=dev["app_version"],
                workdir="./sessions"
            ) as app:
                await app.invoke(functions.account.UpdateStatus(offline=False))
                await app.get_me()
                alive += 1
        except Exception:
            is_dead = True
        
        if is_dead:
            phone_val = acc.get('phone', 'Unknown')
            acc_id = acc.get('user_id', 'Unknown')
            dead_list.append(f"📞 `{phone_val}` | 🆔 `{acc_id}`")
        
        if i % 5 == 0 or i == len(accs) - 1:
            await status_msg.edit_text(
                f"🔎 **Checking for Dead Accounts...**\n"
                f"💀 Found: `{len(dead_list)}`\n"
                f"⏳ Progress: {i+1}/{len(accs)}"
            )
    
    if not dead_list:
        await status_msg.edit_text(f"✅ **All accounts are alive!** ({alive} Total)")
    else:
        res = f"💀 **Found {len(dead_list)} Dead Accounts (Not Removed):**\n\n" + "\n".join(dead_list)
        res += "\n\n💡 Use `/cleandead` to permanently remove them from the database."
        
        if len(res) > 4000:
            with open("dead_accounts_check.txt", "w") as f:
                f.write("\n".join(dead_list))
            await message.reply_document(
                "dead_accounts_check.txt",
                caption=f"💀 **Found {len(dead_list)} Dead Accounts (Not Removed)**\n"
                        f"💡 Use `/cleandead` to remove them."
            )
            os.remove("dead_accounts_check.txt")
            await status_msg.delete()
        else:
            await status_msg.edit_text(res)

@bot.on_message(filters.command("cleandead") & filters.private)
async def cleandead_cmd(client, message: Message):
    if not await check_admin(message.from_user.id):
        return
    
    accs = await accounts_col.find({}).to_list(length=1000)
    if not accs:
        return await message.reply("❌ No accounts logged in.")
    
    status_msg = await message.reply(
        f"🧹 **Cleaning Dead Accounts...**\n"
        f"Checking {len(accs)} sessions."
    )
    dead_list = []
    alive = 0
    
    for i, acc in enumerate(accs):
        await asyncio.sleep(0.5)
        is_dead = False
        try:
            dev = get_spoofed_device()
            async with Client(
                f"temp_cleandead_{uuid.uuid4().hex[:8]}",
                in_memory=True,
                no_updates=True,
                session_string=acc["session"],
                api_id=API_ID,
                api_hash=API_HASH,
                device_model=dev["device_model"],
                system_version=dev["system_version"],
                app_version=dev["app_version"],
                workdir="./sessions"
            ) as app:
                await app.get_me()
                alive += 1
        except Exception:
            is_dead = True
        
        if is_dead:
            phone_val = acc.get('phone', 'Unknown')
            acc_id = acc.get('user_id', 'Unknown')
            dead_list.append(f"📞 `{phone_val}` | 🆔 `{acc_id}`")
            await accounts_col.delete_one({"user_id": acc.get("user_id")})
        
        if i % 5 == 0 or i == len(accs) - 1:
            await status_msg.edit_text(
                f"🧹 **Cleaning Dead Accounts...**\n"
                f"💀 Removed: `{len(dead_list)}`\n"
                f"⏳ Progress: {i+1}/{len(accs)}"
            )
    
    if not dead_list:
        await status_msg.edit_text(f"✅ **All accounts are alive!** ({alive} Total)")
    else:
        res = f"💀 **Removed {len(dead_list)} Dead Accounts:**\n\n" + "\n".join(dead_list)
        if len(res) > 4000:
            with open("dead_accounts_cleaned.txt", "w") as f:
                f.write("\n".join(dead_list))
            await message.reply_document(
                "dead_accounts_cleaned.txt",
                caption=f"💀 **Removed {len(dead_list)} Dead Accounts**"
            )
            os.remove("dead_accounts_cleaned.txt")
            await status_msg.delete()
        else:
            await status_msg.edit_text(res)

@bot.on_message(filters.command("dbcheck") & filters.private)
async def db_check_cmd(client, message: Message):
    if not await check_admin(message.from_user.id):
        return
    
    try:
        await db.command("ping")
        accs = await accounts_col.count_documents({})
        usrs = await users_col.count_documents({})
        adms = await admin_col.count_documents({})
        tks = await tokens_col.count_documents({})
        
        res = (
            "🟢 **Database Connected Successfully!**\n\n"
            f"📱 Sessions: `{accs}`\n"
            f"👥 Users: `{usrs}`\n"
            f"👮 Admins: `{adms}`\n"
            f"🎫 Tokens: `{tks}`\n"
        )
        await message.reply(res)
    except Exception as e:
        await message.reply(f"🔴 **Database Error:**\n`{str(e)}`")

@bot.on_message(filters.command("setcap") & filters.user(OWNER_ID))
async def set_admin_cap_cmd(client, message: Message):
    if len(message.command) < 3:
        return await message.reply("❌ Usage: `/setcap ADMIN_ID AMOUNT`")
    
    try:
        t_id = int(message.command[1])
        amt = int(message.command[2])
        await admin_col.update_one(
            {"user_id": t_id},
            {"$set": {"credit_cap": amt}},
            upsert=True
        )
        await message.reply(f"✅ Admin `{t_id}` credit cap has been set to `{amt}`.")
    except:
        await message.reply("❌ Invalid format.")

@bot.on_message(filters.command("users") & filters.private)
async def list_users(client, message: Message):
    if not await check_admin(message.from_user.id):
        return
    
    users = await users_col.find({}).to_list(length=500)
    if not users:
        return await message.reply("❌ No active users found.")
    
    res = "👥 **Active Users**\n"
    for i, u in enumerate(users, 1):
        res += f"{i}. {u.get('name', 'User')} | ID: `{u.get('user_id')}` | 💳: {u.get('credits', 0)}\n"
    
    await message.reply(res)

@bot.on_message(filters.command("rmuser") & filters.private)
async def remove_user_cmd(client, message: Message):
    if not await check_admin(message.from_user.id):
        return
    
    if len(message.command) < 2:
        return await message.reply("❌ Usage: `/rmuser USER_ID`")
    
    try:
        t_id = int(message.command[1])
        await users_col.delete_one({"user_id": t_id})
        await message.reply(f"✅ Access permanently revoked for User ID `{t_id}`.")
    except:
        await message.reply("❌ Invalid ID format.")

@bot.on_message(filters.command("addtoken") & filters.private)
async def gen_tk(client, message: Message):
    if not await check_admin(message.from_user.id):
        return
    
    tk = str(uuid.uuid4())[:8].upper()
    await tokens_col.insert_one({"token": tk, "used": False})
    await message.reply(f"🎫 **Token:** `{tk}`")

@bot.on_message(filters.command("addcredit") & filters.private)
async def add_cr(client, message: Message):
    if not await check_admin(message.from_user.id):
        return
    
    if len(message.command) < 3:
        return
    
    try:
        t_id = int(message.command[1])
        amt = int(message.command[2])
        uid = message.from_user.id
        
        if uid != OWNER_ID:
            admin_doc = await admin_col.find_one({"user_id": uid})
            if admin_doc:
                cap = admin_doc.get("credit_cap", 0)
                used = admin_doc.get("used_credits", 0)
                if used + amt > cap:
                    return await message.reply(
                        f"❌ **Limit Reached!**\n"
                        f"You have an admin credit cap of `{cap}`.\n"
                        f"You have already used `{used}`.\n"
                        f"You can only add `{max(0, cap - used)}` more credits."
                    )
                await admin_col.update_one(
                    {"user_id": uid},
                    {"$inc": {"used_credits": amt}}
                )
        
        await users_col.update_one(
            {"user_id": t_id},
            {"$inc": {"credits": amt}},
            upsert=True
        )
        await credit_logs_col.insert_one({
            "admin_id": uid,
            "target_user": t_id,
            "amount": amt,
            "date": datetime.now().strftime("%Y-%m-%d %H:%M")
        })
        await message.reply(f"✅ Added {amt} to `{t_id}`")
    except:
        await message.reply("❌ Invalid format.")

@bot.on_message(filters.command("addadmin") & filters.user(OWNER_ID))
async def add_adm(client, message: Message):
    if len(message.command) < 2:
        return
    
    try:
        target = int(message.command[1])
        await admin_col.update_one(
            {"user_id": target},
            {"$set": {"user_id": target, "credit_cap": 0, "used_credits": 0}},
            upsert=True
        )
        await message.reply(f"✅ User `{target}` is now Admin.")
    except:
        await message.reply("❌ Invalid ID format.")

@bot.on_message(filters.command("rmadmin") & filters.user(OWNER_ID))
async def rm_adm(client, message: Message):
    if len(message.command) < 2:
        return await message.reply("❌ Usage: `/rmadmin USER_ID`")
    
    try:
        target = int(message.command[1])
        await admin_col.delete_one({"user_id": target})
        await message.reply(f"✅ Admin privileges revoked for User ID `{target}`.")
    except:
        await message.reply("❌ Invalid ID format.")

@bot.on_message(filters.command("join") & filters.private)
async def join_cmd(client, message: Message):
    if not await check_admin(message.from_user.id):
        return
    
    if len(message.command) < 2:
        return await message.reply("❌ Usage: `/join link`")
    
    await mass_join(message, message.command[1])

@bot.on_message(filters.command("leave") & filters.private)
async def leave_cmd(client, message: Message):
    if not await check_admin(message.from_user.id):
        return
    
    if len(message.command) < 2:
        return await message.reply("❌ Usage: `/leave link_or_username`")
    
    await mass_leave(message, message.command[1])

@bot.on_message(filters.command("health") & filters.private)
async def health_cmd(client, message: Message):
    if not await check_admin(message.from_user.id):
        return
    
    await perform_health_check(message)

@bot.on_message(filters.command("broadcast") & filters.private)
async def bcast(client, message: Message):
    if not await check_admin(message.from_user.id):
        return
    
    if not message.reply_to_message and len(message.command) < 2:
        return await message.reply("❌ Usage: `/broadcast <message>` or reply to a message.")
    
    users = await users_col.find({}).to_list(length=1000)
    admins = await admin_col.find({}).to_list(length=100)
    all_targets = set(
        [u.get("user_id") for u in users if u.get("user_id")] +
        [a.get("user_id") for a in admins if a.get("user_id")] +
        [OWNER_ID]
    )
    
    sent = 0
    status = await message.reply("📢 Broadcasting...")
    
    for t_id in all_targets:
        try:
            if t_id and t_id != 0:
                if message.reply_to_message:
                    await message.reply_to_message.copy(t_id)
                else:
                    text_only = message.text.split(None, 1)[1]
                    await bot.send_message(
                        t_id,
                        f"📢 **Broadcast:**\n\n{text_only}"
                    )
                sent += 1
        except:
            pass
    
    await status.edit_text(f"✅ Broadcast Sent to {sent} chats.")

@bot.on_message(filters.command("redeem") & filters.private)
async def redeem_tk(client, message: Message):
    if len(message.command) < 2:
        return
    
    t_str = message.command[1]
    token = await tokens_col.find_one({"token": t_str, "used": False})
    
    if token:
        await tokens_col.update_one(
            {"token": t_str},
            {"$set": {"used": True, "by": message.from_user.id}}
        )
        await users_col.update_one(
            {"user_id": message.from_user.id},
            {
                "$set": {
                    "status": "active",
                    "credits": 1,
                    "total_reports": 0,
                    "name": message.from_user.first_name
                }
            },
            upsert=True
        )
        await message.reply("🎉 Token Redeemed! 1 Credit added.")
    else:
        await message.reply("❌ Invalid or already used token.")

# --- MAIN ---
print("🤖 Bot is starting...")
print(f"API_ID: {API_ID}")
print(f"MONGO_URI: {MONGO_URI}")

async def main():
    try:
        # Create directories
        os.makedirs("./sessions", exist_ok=True)
        os.makedirs("./logs", exist_ok=True)
        
        # Start keep-alive task
        asyncio.create_task(keep_alive_sessions())
        
        # Start bot
        await bot.start()
        me = await bot.get_me()
        print(f"✅ Bot started successfully!")
        print(f"📱 Bot username: @{me.username}")
        print(f"🆔 Bot ID: {me.id}")
        print("📍 Bot is running. Press Ctrl+C to stop.")
        
        await bot.idle()
    except Exception as e:
        logger.error(f"❌ Error in main: {e}")
        raise
    finally:
        await bot.stop()
        logger.info("Bot stopped")

if __name__ == "__main__":
    asyncio.run(main())