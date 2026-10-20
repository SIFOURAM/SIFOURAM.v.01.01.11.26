"""One-time reset approved for the final SI FOUR AM revision."""
import asyncio
import os
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
        {"$set": {"name": "Baazulfikar", "role": "owner", "active": True}},
    )
    for collection in [
        "coach_chats",
        "expenses",
        "handovers",
        "withdrawals",
        "inventory_tx",
        "menu_stock_tx",
        "rider_stock",
        "wastage",
    ]:
        await db[collection].delete_many({})
    await db.materials.update_many({}, {"$set": {"stock": 0}})
    await db.menus.update_many({}, {"$set": {"stock": 0}})
    client.close()


if __name__ == "__main__":
    asyncio.run(reset())