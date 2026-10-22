# UI seed for iteration 34 owner onboarding: python tests/ui_seed_iter34.py rider|stock|clean
import os
import sys
import uuid
from datetime import datetime, timedelta, timezone

import bcrypt
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv("/app/backend/.env")
db = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
USERNAME, PIN = "test_ui34_rider", "246810"
PHOTO = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
TODAY = datetime.now(timezone(timedelta(hours=7))).strftime("%Y-%m-%d")


def rider():
    db.users.insert_one({
        "id": str(uuid.uuid4()), "name": "TEST UI Rider34", "username": USERNAME, "email": "", "whatsapp": "",
        "role": "rider", "active": True, "password_hash": bcrypt.hashpw(b"x", bcrypt.gensalt()).decode(),
        "pin_hash": bcrypt.hashpw(PIN.encode(), bcrypt.gensalt()).decode(), "photo": None, "banks": [],
        "settings": {"theme": "dark", "language": "id", "notifications": True},
        "created_at": datetime.now(timezone.utc).isoformat(),
    })


def stock():
    r = db.users.find_one({"username": USERNAME})
    menus = list(db.menus.find({}, {"_id": 0}).sort("order", 1).limit(2))
    db.rider_stock.insert_one({
        "id": str(uuid.uuid4()), "rider_id": r["id"], "rider_name": r["name"], "pic_id": "owner", "pic_name": "Baazulfikar",
        "date": TODAY, "time": "08:00", "items": {menus[0]["id"]: 4, menus[1]["id"]: 2},
        "detail": {menus[0]["name"]: 4, menus[1]["name"]: 2}, "total": 6, "photo": PHOTO, "created_by": "Baazulfikar",
        "verified_at": None, "verified_by": None, "verified_by_name": None, "verification_photo": None,
    })


def clean():
    ids = [u["id"] for u in db.users.find({"username": {"$regex": "^test_ui34_"}}, {"id": 1})]
    for c in ("rider_stock", "menu_stock_tx", "sales", "eod", "attendance"):
        db[c].delete_many({"rider_id": {"$in": ids}})
    db.files.delete_many({"user_id": {"$in": ids}})
    db.sessions.delete_many({"user_id": {"$in": ids}})
    db.audit_logs.delete_many({"user_id": {"$in": ids}})
    db.users.delete_many({"id": {"$in": ids}})


{"rider": rider, "stock": stock, "clean": clean}[sys.argv[1]]()
print("ok", sys.argv[1])
