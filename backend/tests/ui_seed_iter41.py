# Iter41 UI seed/cleanup for procurement: `python ui_seed_iter41.py seed|cleanup`
import os
import sys
import json
import random
import requests
from dotenv import load_dotenv
from pymongo import MongoClient
from PIL import Image, ImageDraw

load_dotenv("/app/frontend/.env")
load_dotenv("/app/backend/.env")
API = os.environ["REACT_APP_BACKEND_URL"].rstrip("/") + "/api"
db = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
STATE = "/tmp/ui_iter41.json"


def login(i, p):
    s = requests.Session()
    r = s.post(f"{API}/auth/identify", json={"identifier": i, "terms_accepted": True, "privacy_accepted": True})
    r.raise_for_status()
    s.post(f"{API}/auth/login", json={"account_token": r.json()["account_token"], "pin": p}).raise_for_status()
    return s


def seed():
    o = login("baa", "130994")
    users = {}
    for role in ["admin", "barteam", "rider"]:
        un = f"qa41ui_{role}"
        db.users.delete_many({"username": un})
        r = o.post(f"{API}/users", json={"name": f"QA41 {role}", "username": un, "role": role, "pin": "246813"})
        r.raise_for_status()
        users[role] = r.json()["id"]
    img = Image.new("RGB", (300, 400), "white")
    d = ImageDraw.Draw(img)
    for i in range(18):
        d.text((10, 10 + i * 20), f"NOTA {i} Rp {random.randint(1000, 99999)}", fill="black")
    img.save("/tmp/qa41_receipt.png")
    json.dump({"users": users, "stocks": {m["id"]: m.get("stock", 0) for m in db.materials.find({}, {"_id": 0})}}, open(STATE, "w"))
    print(json.dumps(users))


def cleanup():
    st = json.load(open(STATE))
    ids = list(st["users"].values())
    pos = [p["id"] for p in db.purchase_orders.find({"requested_by": {"$in": ids}}, {"id": 1})]
    for tx in db.inventory_tx.find({"purchase_order_id": {"$in": pos}}):
        db.materials.update_one({"id": tx["material_id"]}, {"$inc": {"stock": -tx["qty"]}})
    db.inventory_tx.delete_many({"purchase_order_id": {"$in": pos}})
    db.notifications.delete_many({"$or": [{"ref_id": {"$in": pos}}, {"for_user": {"$in": ids}}]})
    db.po_share_audit.delete_many({"po_id": {"$in": pos}})
    db.files.delete_many({"folder": "purchase_orders", "user_id": {"$in": ids}})
    db.purchase_orders.delete_many({"id": {"$in": pos}})
    db.sessions.delete_many({"user_id": {"$in": ids}})
    db.users.delete_many({"id": {"$in": ids}})
    now = {m["id"]: m.get("stock", 0) for m in db.materials.find({}, {"_id": 0})}
    print("removed POs", len(pos), "stock restored:", now == st["stocks"])


if __name__ == "__main__":
    seed() if sys.argv[1] == "seed" else cleanup()
