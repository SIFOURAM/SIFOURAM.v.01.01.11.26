"""One-time reset approved for the final SI FOUR AM revision."""
import asyncio
import os
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient


load_dotenv(Path(__file__).parent / ".env")


async def reset():
    client = AsyncIOMotorClient(os.environ["MONGO_URL"])
    db = client[os.environ["DB_NAME"]]
    await db.users.delete_many({"username": {"$ne": "baa"}})
    await db.users.update_one(
        {"username": "baa"},
        {"$set": {
            "name": "Baazulfikar",
            "email": "baazulfikar@gmail.com",
            "role": "owner",
            "active": True,
        }},
    )
    for collection in [
        "attendance",
        "broadcasts",
        "coach_chats",
        "customers",
        "deposits",
        "eod",
        "expenses",
        "finances",
        "gps",
        "handovers",
        "inventory_tx",
        "invoices",
        "login_attempts",
        "menu_stock_tx",
        "notifications",
        "payment_accounts",
        "purchase_orders",
        "rank_resets",
        "rider_stock",
        "sales",
        "sessions",
        "wastage",
        "withdrawals",
    ]:
        await db[collection].delete_many({})
    await db.files.update_many(
        {"folder": {"$ne": "menus"}},
        {"$set": {"is_deleted": True, "deleted_at": datetime.now(timezone.utc).isoformat()}},
    )
    await db.materials.update_many({}, {"$set": {"stock": 0}})
    await db.menus.update_many({}, {"$set": {"stock": 0}})
    await db.audit_logs.delete_many({})
    await db.audit_logs.insert_one({
        "id": "final-operational-reset",
        "action": "system.operational_reset",
        "user_id": None,
        "ip": "local",
        "outcome": "allowed",
        "detail": "Operational data reset; masters and Owner retained.",
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    client.close()


if __name__ == "__main__":
    asyncio.run(reset())