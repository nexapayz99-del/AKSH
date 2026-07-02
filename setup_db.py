# setup_db.py
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
import os

load_dotenv()

async def setup_indexes():
    client = AsyncIOMotorClient(os.getenv("MONGO_URI"))
    db = client["telegram_bot"]
    
    # Users collection
    await db.authorized_users.create_index("user_id", unique=True)
    
    # Sessions collection
    await db.sessions.create_index("user_id", unique=True)
    await db.sessions.create_index("phone")
    
    # Reports collection
    await db.report_logs.create_index([("user_id", 1), ("timestamp", -1)])
    await db.report_logs.create_index("status")
    
    # Tokens collection
    await db.keys.create_index("token", unique=True)
    
    # Credit logs
    await db.credit_logs.create_index([("admin_id", 1), ("date", -1)])
    
    print("✅ Database indexes created successfully!")

if __name__ == "__main__":
    asyncio.run(setup_indexes())
