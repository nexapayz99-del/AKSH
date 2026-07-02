# setup_db.py
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

async def setup_database():
    """Setup MongoDB indexes and initial data"""
    try:
        # Connect to MongoDB
        MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
        client = AsyncIOMotorClient(MONGO_URI)
        db = client["telegram_bot"]
        
        logger.info("🔄 Setting up database indexes...")
        
        # Users collection indexes
        await db.authorized_users.create_index("user_id", unique=True)
        logger.info("✅ Created index on authorized_users.user_id")
        
        # Sessions collection indexes
        await db.sessions.create_index("user_id", unique=True)
        await db.sessions.create_index("phone")
        logger.info("✅ Created indexes on sessions")
        
        # Report logs indexes
        await db.report_logs.create_index([("user_id", 1), ("timestamp", -1)])
        await db.report_logs.create_index("status")
        logger.info("✅ Created indexes on report_logs")
        
        # Tokens collection indexes
        await db.keys.create_index("token", unique=True)
        logger.info("✅ Created index on keys.token")
        
        # Credit logs indexes
        await db.credit_logs.create_index([("admin_id", 1), ("date", -1)])
        logger.info("✅ Created indexes on credit_logs")
        
        # Refund logs indexes
        await db.refund_logs.create_index([("user_id", 1), ("date", -1)])
        logger.info("✅ Created indexes on refund_logs")
        
        # API receipts indexes
        await db.api_receipts.create_index([("user_id", 1), ("timestamp", -1)])
        logger.info("✅ Created indexes on api_receipts")
        
        # Admins collection indexes
        await db.admins.create_index("user_id", unique=True)
        logger.info("✅ Created index on admins.user_id")
        
        logger.info("✅ Database setup completed successfully!")
        
        # Show existing data counts
        accs = await db.sessions.count_documents({})
        users = await db.authorized_users.count_documents({})
        admins = await db.admins.count_documents({})
        tokens = await db.keys.count_documents({})
        
        logger.info(f"📊 Current data:")
        logger.info(f"  - Sessions: {accs}")
        logger.info(f"  - Users: {users}")
        logger.info(f"  - Admins: {admins}")
        logger.info(f"  - Tokens: {tokens}")
        
        client.close()
        return True
        
    except Exception as e:
        logger.error(f"❌ Database setup failed: {e}")
        return False

async def reset_database():
    """Reset database (DANGEROUS - Only use for development)"""
    confirm = input("⚠️  This will delete ALL data. Type 'YES' to confirm: ")
    if confirm != "YES":
        logger.info("❌ Reset cancelled")
        return False
    
    try:
        MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
        client = AsyncIOMotorClient(MONGO_URI)
        db = client["telegram_bot"]
        
        logger.info("🗑️  Dropping database...")
        await db.drop_collection("sessions")
        await db.drop_collection("authorized_users")
        await db.drop_collection("keys")
        await db.drop_collection("admins")
        await db.drop_collection("report_logs")
        await db.drop_collection("refund_logs")
        await db.drop_collection("api_receipts")
        await db.drop_collection("credit_logs")
        
        logger.info("✅ Database reset completed")
        client.close()
        return True
        
    except Exception as e:
        logger.error(f"❌ Reset failed: {e}")
        return False

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--reset":
        asyncio.run(reset_database())
    else:
        asyncio.run(setup_database())