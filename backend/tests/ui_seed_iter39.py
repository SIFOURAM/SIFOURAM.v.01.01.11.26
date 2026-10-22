# Iteration 39 UI seed: temp rider with verified rider stock + central menu stock, writes /tmp/iter39_seed.json
import json
import os
import uuid
from datetime import datetime, timedelta, timezone

import bcrypt
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv("/app/backend/.env")
db = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
WIB = timezone(timedelta(hours=7))
today = datetime.now(WIB).strftime("%Y-%m-%d")
menus = list(db.menus.find({"active": {"$ne": False}}, {"_id": 0}).sort("order", 1))
m1, m2 = menus[0], menus[1]
rid = "test-ui-rider-39"
db.users.delete_many({"id": rid})
db.users.insert_one({"id": rid, "name": "TEST UI Rider39", "username": "test_ui_rid39", "role": "rider", "active": True,
                     "pin_hash": bcrypt.hashpw(b"246813", bcrypt.gensalt()).decode(), "whatsapp": "", "email": "",
                     "settings": {}, "created_at": datetime.now(timezone.utc).isoformat()})
db.rider_stock.delete_many({"rider_id": rid})
db.rider_stock.insert_one({"id": "test-rs-39", "rider_id": rid, "rider_name": "TEST UI Rider39", "date": today, "items": {m1["id"]: 10, m2["id"]: 10},
                           "detail": {}, "total": 20, "photo": None, "verified_at": datetime.now(timezone.utc).isoformat(), "verified_by": rid})
db.menus.update_one({"id": m1["id"]}, {"$set": {"stock": 20}})
db.menus.update_one({"id": m2["id"]}, {"$set": {"stock": 5}})
out = {"rider_id": rid, "m1": m1["id"], "m1_name": m1["name"], "m2": m2["id"], "today": today}
json.dump(out, open("/tmp/iter39_seed.json", "w"))
print(out)
